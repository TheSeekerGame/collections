// SPDX-License-Identifier: MIT
pragma solidity 0.8.17;

import { ERC721SeaDrop } from "seadrop/ERC721SeaDrop.sol";

import { ISeekerRenderer } from "./ISeekerRenderer.sol";

/**
 * @title  SEEKER NET
 * @notice OpenSea's ERC721SeaDrop (seadrop commit 0ee428b, the version OpenSea
 *         Studio deploys) plus the charge game, played entirely on-chain.
 *
 *         Dormant pool. At reveal every seeker gets a random starting charge
 *         of 0-8,500 and then generates 50 charge a day. When a dormant
 *         seeker moves (any transfer), it keeps 75% of its charge and the
 *         other 25% is split equally among the other dormant seekers. A
 *         seeker whose charge goes over 9,000 is activated for good.
 *
 *         Activated pool. An activation is recorded the first time the seeker
 *         is touched (activate() or a move), at exactly the floor: 9,000 plus
 *         the smallest unit. Recorded seekers keep generating 50 a day and
 *         receive charge only from other recorded seekers. When one moves,
 *         it keeps 75% of its charge above the floor and the other 25% is
 *         split equally among the others.
 *
 *         Moves before the reveal do nothing. Charge has 18 decimals. Shares
 *         are tracked with running per-seeker totals (accD, accA), so a move
 *         costs the same gas however many seekers there are.
 *
 *         The game code never makes a transfer fail: it makes no outside calls
 *         and every subtraction and division in it is guarded.
 */
contract SeekerNet is ERC721SeaDrop {
    uint256 public constant ONE = 1e18;
    uint256 public constant RATE_PER_DAY = 50;
    uint256 public constant DAY = 86400;
    uint256 public constant START_MAX = 8500;
    uint256 public constant THRESHOLD = 9000;
    /// @notice Share of a moving seeker's charge (above the floor, once
    ///         activated) that goes to the others, in basis points.
    uint256 public constant TAX_BPS = 2500;
    /// @notice Activation needs charge >= FLOOR, i.e. over 9,000.
    uint256 public constant FLOOR = THRESHOLD * ONE + 1;
    uint256 public constant ART_COUNT = 2222;
    uint256 public constant REFRESH_COOLDOWN = 3600;
    /// @notice The reveal seed uses the hash of a block this many blocks after
    ///         reveal() (block.number here is Ethereum's block number).
    uint256 public constant REVEAL_DELAY = 2;

    uint256 private constant _GEN_PER_SEC_NUM = RATE_PER_DAY * ONE;

    /// @dev One storage slot per token.
    ///      Unrecorded: charge = stored + generation since lastMove + dormant
    ///      shares since snap (accD). lastMove is 0 while the token hasn't
    ///      moved since the reveal; then its stored charge is its starting
    ///      charge, computed from the seed.
    ///      Recorded: charge = FLOOR + stored + generation since lastMove +
    ///      activated shares since snap (accA).
    struct Token {
        uint40 lastMove;
        uint112 snap;
        uint96 stored;
        bool activated;
    }

    /// @notice Token status codes used by statusOf and chargesOf.
    uint8 public constant DORMANT = 0;
    uint8 public constant ACTIVATED = 1; // over 9,000, not recorded yet
    uint8 public constant RECORDED = 2; // activated and recorded
    uint8 public constant NONEXISTENT = 3; // burned or not minted

    mapping(uint256 => Token) internal _tokens;

    /// @notice Charge handed to each dormant seeker since the reveal.
    uint112 public accD;
    /// @notice Charge handed to each recorded activated seeker.
    uint112 public accA;

    /// @notice Replaceable display contract; 0 = use the base's baseURI.
    address public renderer;
    /// @notice 0 until the reveal.
    uint40 public revealTime;
    /// @notice Number of existing seekers whose activation is recorded.
    uint32 public activatedCount;
    bool public rendererLocked;

    uint40 public lastRefreshAll;
    /// @notice Block whose hash completes the seed; 0 until reveal().
    uint64 public revealBlock;

    /// @notice keccak256 of the owner's reveal secret, set before the mint.
    bytes32 public seedCommit;
    /// @notice The secret, published by reveal().
    bytes32 public revealSecret;
    /// @notice Fixed at the reveal. Drives starting charges and the art order.
    bytes32 public seed;

    /// @dev ERC-4906 single-token refresh signal.
    event MetadataUpdate(uint256 _tokenId);
    event SeedCommitted(bytes32 commit);
    event RevealRequested(bytes32 secret, uint256 revealBlock);
    event Revealed(bytes32 seed);
    event Activated(uint256 indexed tokenId);
    event ChargeReleased(
        uint256 indexed tokenId,
        uint256 charge,
        uint256 recipients,
        bool activatedPool
    );
    event RendererUpdated(address renderer);
    event RendererLocked(address renderer);

    error SeedNotCommitted();
    error ArtSupplyExceeded();
    error MintAlreadyStarted();
    error AlreadyRevealed();
    error NoRevealPending();
    error TooEarly();
    error NotRevealed();
    error BadSecret();
    error TokenDoesNotExist();
    error NotEligible(uint256 tokenId);
    error RefreshCooldown();
    error RendererIsLocked();
    error NoRenderer();

    constructor(
        string memory name,
        string memory symbol,
        address[] memory allowedSeaDrop
    ) ERC721SeaDrop(name, symbol, allowedSeaDrop) {}

    // ---------------------------------------------------------------------
    // Game hook
    // ---------------------------------------------------------------------

    function _afterTokenTransfers(
        address from,
        address to,
        uint256 startTokenId,
        uint256 quantity
    ) internal virtual override {
        super._afterTokenTransfers(from, to, startTokenId, quantity);

        if (from == address(0)) {
            // Minting needs the reveal secret committed first, so the
            // commitment provably comes before every mint.
            if (seedCommit == bytes32(0)) revert SeedNotCommitted();
            // One artwork per token: never more than ART_COUNT tokens,
            // whatever maxSupply is set to (ERC721A has already counted
            // this batch).
            if (_totalMinted() > ART_COUNT) revert ArtSupplyExceeded();
            if (revealTime != 0) _initMinted(startTokenId, quantity);
        } else if (to == address(0)) {
            if (_tokens[startTokenId].activated) --activatedCount;
        } else if (revealTime != 0) {
            _move(startTokenId);
        }
    }

    /// @dev Tokens minted after the reveal start with their starting charge
    ///      but don't collect anything from before their mint.
    function _initMinted(uint256 startTokenId, uint256 quantity) private {
        uint40 nowTs = uint40(block.timestamp);
        uint112 a = accD;
        uint256 end = startTokenId + quantity;
        for (uint256 id = startTokenId; id < end; ) {
            _tokens[id] = Token(nowTs, a, uint96(_start(id)), false);
            unchecked {
                ++id;
            }
        }
    }

    function _move(uint256 id) private {
        Token memory t = _tokens[id];
        uint40 nowTs = uint40(block.timestamp);
        uint256 others;
        uint256 c;
        uint112 a;

        if (!t.activated) {
            c = _dormantCharge(id, t);
            if (c >= FLOOR) {
                // Crossed 9,000 but not recorded yet: the move records it at
                // the floor and shares nothing.
                _record(id);
                return;
            }
            uint256 supply = totalSupply();
            uint256 rec = activatedCount;
            others = supply > rec + 1 ? supply - rec - 1 : 0;
            a = accD;
            if (others != 0) {
                uint256 tax = (c * TAX_BPS) / 10_000;
                a = _addShare(a, tax / others);
                accD = a;
                c -= tax;
                emit ChargeReleased(id, tax, others, false);
            }
        } else {
            c = _activatedCharge(t) - FLOOR; // charge above the floor
            uint256 rec = activatedCount;
            others = rec > 1 ? rec - 1 : 0;
            a = accA;
            if (others != 0) {
                uint256 tax = (c * TAX_BPS) / 10_000;
                a = _addShare(a, tax / others);
                accA = a;
                c -= tax;
                emit ChargeReleased(id, tax, others, true);
            }
        }
        // keeps the rest (75%); with nobody to share with, it keeps all of it
        _tokens[id] = Token(nowTs, a, _cap96(c), t.activated);
        emit MetadataUpdate(id);
    }

    function _record(uint256 id) private {
        _tokens[id] = Token(uint40(block.timestamp), accA, 0, true);
        unchecked {
            ++activatedCount; // at most the supply
        }
        emit Activated(id);
        emit MetadataUpdate(id);
    }

    /// @dev Saturates instead of overflowing, so a transfer can't revert here.
    ///      Unreachable in practice: a dormant share is below 2,250 * 1e18 and
    ///      uint112 holds ~5.2e33.
    function _addShare(uint112 acc, uint256 share)
        private
        pure
        returns (uint112)
    {
        uint256 sum = uint256(acc) + share;
        return sum > type(uint112).max ? type(uint112).max : uint112(sum);
    }

    /// @dev Same for a stored charge (uint96 holds ~79 billion charge).
    function _cap96(uint256 c) private pure returns (uint96) {
        return c > type(uint96).max ? type(uint96).max : uint96(c);
    }

    // ---------------------------------------------------------------------
    // Charge math (all values scaled by ONE)
    // ---------------------------------------------------------------------

    function _gen(uint256 since) private view returns (uint256) {
        return
            block.timestamp > since
                ? ((block.timestamp - since) * _GEN_PER_SEC_NUM) / DAY
                : 0;
    }

    function _start(uint256 id) private view returns (uint256) {
        return
            (uint256(keccak256(abi.encode(seed, id))) % (START_MAX + 1)) * ONE;
    }

    /// @dev Unrecorded tokens only.
    function _dormantCharge(uint256 id, Token memory t)
        private
        view
        returns (uint256 c)
    {
        if (t.lastMove == 0) {
            // untouched since the reveal: its starting charge
            c = _start(id) + _gen(revealTime) + accD;
        } else {
            c = t.stored + _gen(t.lastMove) + (accD - t.snap);
        }
    }

    /// @dev Recorded tokens only.
    function _activatedCharge(Token memory t) private view returns (uint256) {
        return FLOOR + t.stored + _gen(t.lastMove) + (accA - t.snap);
    }

    function _chargeAndStatus(uint256 id)
        private
        view
        returns (uint256 c, uint8 status)
    {
        if (revealTime == 0) return (0, DORMANT);
        Token memory t = _tokens[id];
        if (t.activated) return (_activatedCharge(t), RECORDED);
        c = _dormantCharge(id, t);
        if (c >= FLOOR) return (FLOOR, ACTIVATED);
        return (c, DORMANT);
    }

    function _requireExists(uint256 id) private view {
        if (!_exists(id)) revert TokenDoesNotExist();
    }

    // ---------------------------------------------------------------------
    // Anyone
    // ---------------------------------------------------------------------

    /// @notice Records the activation of a seeker that is over 9,000.
    function activate(uint256 id) external {
        if (revealTime == 0) revert NotRevealed();
        _requireExists(id);
        Token memory t = _tokens[id];
        if (t.activated || _dormantCharge(id, t) < FLOOR) {
            revert NotEligible(id);
        }
        _record(id);
    }

    /// @notice Records every eligible seeker in `ids`, skipping the rest.
    /// @return n The number of activations recorded.
    function activateMany(uint256[] calldata ids) external returns (uint256 n) {
        if (revealTime == 0) return 0;
        uint256 len = ids.length;
        for (uint256 i; i < len; ) {
            uint256 id = ids[i];
            if (_exists(id)) {
                Token memory t = _tokens[id];
                if (!t.activated && _dormantCharge(id, t) >= FLOOR) {
                    _record(id);
                    unchecked {
                        ++n;
                    }
                }
            }
            unchecked {
                ++i;
            }
        }
    }

    /// @notice Asks marketplaces to re-read every token. At most hourly.
    function refreshAll() external {
        if (block.timestamp < uint256(lastRefreshAll) + REFRESH_COOLDOWN) {
            revert RefreshCooldown();
        }
        lastRefreshAll = uint40(block.timestamp);
        if (totalSupply() != 0) emit BatchMetadataUpdate(1, _nextTokenId() - 1);
    }

    /// @notice Asks marketplaces to re-read tokens fromId..toId (inclusive,
    ///         clipped to the minted range), one ERC-4906 MetadataUpdate each.
    ///         Unlike refreshAll's single batch signal, OpenSea acts on these
    ///         per-token signals right away. Anyone; costs only gas.
    function refreshTokens(uint256 fromId, uint256 toId) external {
        if (fromId < 1) fromId = 1;
        uint256 last = _nextTokenId() - 1;
        if (toId > last) toId = last;
        for (uint256 id = fromId; id <= toId; ) {
            emit MetadataUpdate(id);
            unchecked {
                ++id;
            }
        }
    }

    // ---------------------------------------------------------------------
    // Owner
    // ---------------------------------------------------------------------

    /// @notice Commits to the reveal secret: `commit = keccak256(secret)`.
    ///         Only before the first mint (it can be replaced until then).
    function commitSeed(bytes32 commit) external onlyOwner {
        if (_totalMinted() != 0) revert MintAlreadyStarted();
        if (revealBlock != 0) revert AlreadyRevealed();
        seedCommit = commit;
        emit SeedCommitted(commit);
    }

    /// @notice Step 1 of the reveal: publishes the secret and picks a block a
    ///         little in the future. Nobody, the owner included, can know
    ///         that block's hash yet, so nobody can choose the outcome.
    function reveal(bytes32 secret) external onlyOwner {
        if (revealBlock != 0) revert AlreadyRevealed();
        bytes32 commit = seedCommit;
        if (
            commit == bytes32(0) ||
            keccak256(abi.encodePacked(secret)) != commit
        ) revert BadSecret();
        revealSecret = secret;
        uint256 target = block.number + REVEAL_DELAY;
        revealBlock = uint64(target);
        emit RevealRequested(secret, target);
    }

    /// @notice Step 2, anyone, once the chosen block has passed: fixes the
    ///         seed and starts the game. If more than 256 blocks went by
    ///         (its hash is gone), it picks a new block instead.
    function finalizeReveal() external {
        uint256 target = revealBlock;
        if (target == 0 || revealTime != 0) revert NoRevealPending();
        if (block.number <= target) revert TooEarly();
        bytes32 bh = blockhash(target);
        if (bh == bytes32(0)) {
            target = block.number + REVEAL_DELAY;
            revealBlock = uint64(target);
            emit RevealRequested(revealSecret, target);
            return;
        }
        bytes32 s = keccak256(abi.encode(revealSecret, bh, address(this)));
        seed = s;
        revealTime = uint40(block.timestamp);
        emit Revealed(s);
        if (totalSupply() != 0) emit BatchMetadataUpdate(1, _nextTokenId() - 1);
    }

    function setRenderer(address newRenderer) external onlyOwner {
        if (rendererLocked) revert RendererIsLocked();
        renderer = newRenderer;
        emit RendererUpdated(newRenderer);
        if (totalSupply() != 0) emit BatchMetadataUpdate(1, _nextTokenId() - 1);
    }

    /// @notice Permanently fixes the renderer address. The renderer has its
    ///         own lock for its settings.
    function lockRenderer() external onlyOwner {
        address r = renderer;
        if (r == address(0)) revert NoRenderer();
        rendererLocked = true;
        emit RendererLocked(r);
    }

    // ---------------------------------------------------------------------
    // Views
    // ---------------------------------------------------------------------

    function tokenURI(uint256 tokenId)
        public
        view
        virtual
        override
        returns (string memory)
    {
        address r = renderer;
        if (r == address(0)) return super.tokenURI(tokenId);
        if (!_exists(tokenId)) revert URIQueryForNonexistentToken();
        return ISeekerRenderer(r).tokenURI(tokenId);
    }

    function isRevealed() public view returns (bool) {
        return revealTime != 0;
    }

    /// @notice Current charge, scaled by ONE. A seeker that crossed 9,000
    ///         but isn't recorded shows the floor. 0 before the reveal.
    function chargeOf(uint256 id) external view returns (uint256 c) {
        _requireExists(id);
        (c, ) = _chargeAndStatus(id);
    }

    /// @notice DORMANT, ACTIVATED (over 9,000, not recorded) or RECORDED.
    function statusOf(uint256 id) external view returns (uint8 status) {
        _requireExists(id);
        (, status) = _chargeAndStatus(id);
    }

    function isActivated(uint256 id) external view returns (bool) {
        _requireExists(id);
        (, uint8 status) = _chargeAndStatus(id);
        return status != DORMANT;
    }

    function isRecorded(uint256 id) external view returns (bool) {
        _requireExists(id);
        return _tokens[id].activated;
    }

    /// @notice Uncapped dormant-pool charge of an unrecorded seeker (0 once
    ///         recorded, or before the reveal).
    function dormantChargeOf(uint256 id) external view returns (uint256) {
        _requireExists(id);
        Token memory t = _tokens[id];
        if (revealTime == 0 || t.activated) return 0;
        return _dormantCharge(id, t);
    }

    /// @notice The random starting charge (0 before the reveal).
    function startChargeOf(uint256 id) external view returns (uint256) {
        _requireExists(id);
        return revealTime == 0 ? 0 : _start(id);
    }

    /// @notice Which of the 2,222 artworks (0-based, provenance order) the
    ///         token shows. Fixed at the reveal.
    function artIndexOf(uint256 id) external view returns (uint256) {
        _requireExists(id);
        if (revealTime == 0) revert NotRevealed();
        return (id - 1 + (uint256(seed) % ART_COUNT)) % ART_COUNT;
    }

    /// @notice Charges and statuses for token IDs `fromId..toId` (inclusive,
    ///         clipped to the minted range). Burned tokens are NONEXISTENT.
    function chargesOf(uint256 fromId, uint256 toId)
        external
        view
        returns (uint256[] memory charges, uint8[] memory statuses)
    {
        if (fromId < 1) fromId = 1;
        uint256 last = _nextTokenId() - 1;
        if (toId > last) toId = last;
        uint256 n = toId >= fromId ? toId - fromId + 1 : 0;
        charges = new uint256[](n);
        statuses = new uint8[](n);
        for (uint256 i; i < n; ) {
            uint256 id = fromId + i;
            if (_exists(id)) {
                (charges[i], statuses[i]) = _chargeAndStatus(id);
            } else {
                statuses[i] = NONEXISTENT;
            }
            unchecked {
                ++i;
            }
        }
    }

    /// @notice Raw per-token game state, for indexers and checks.
    function tokenState(uint256 id)
        external
        view
        returns (
            uint256 lastMove,
            uint256 snap,
            uint256 stored,
            bool recorded
        )
    {
        Token memory t = _tokens[id];
        return (t.lastMove, t.snap, t.stored, t.activated);
    }

    /// @notice Number of minted tokens (including burned ones).
    function totalMinted() external view returns (uint256) {
        return _totalMinted();
    }
}
