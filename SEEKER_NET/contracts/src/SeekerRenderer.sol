// SPDX-License-Identifier: MIT
pragma solidity 0.8.17;

import { Base64 } from "openzeppelin-contracts/utils/Base64.sol";
import { Strings } from "openzeppelin-contracts/utils/Strings.sol";
import { SSTORE2 } from "solmate/utils/SSTORE2.sol";
import { TwoStepOwnable } from "utility-contracts/TwoStepOwnable.sol";

import { ISeekerRenderer } from "./ISeekerRenderer.sol";

interface ISeekerNetCore {
    function isRevealed() external view returns (bool);

    function artIndexOf(uint256 id) external view returns (uint256);

    function chargeOf(uint256 id) external view returns (uint256);

    function statusOf(uint256 id) external view returns (uint8);

    function startChargeOf(uint256 id) external view returns (uint256);

    function seed() external view returns (bytes32);

    function accD() external view returns (uint256);

    function revealTime() external view returns (uint256);

    function tokenState(uint256 id)
        external
        view
        returns (
            uint256 lastMove,
            uint256 snap,
            uint256 stored,
            bool recorded
        );
}

/**
 * @title  SEEKER NET renderer
 * @notice Builds each token's metadata JSON on-chain from the core's live
 *         game state:
 *         - which artwork a token shows (artOf): the rarer the seeker,
 *           the lower the starting charge it goes with. The token with the
 *           lowest starting charge shows the first artwork of chargeOrder,
 *           and so on. Starting charges come from the reveal seed, so nobody
 *           chooses the result. Without a chargeOrder: the core's artIndexOf.
 *         - image: the activated GIF of that artwork, or one of its dormant
 *           stills, picked by how much charge the seeker has (stageOf)
 *         - traits: the artwork's traits, plus Status, Charge (whole number),
 *           Starting Charge and, for dormant seekers, Discharge: the charge
 *           the seeker gave up the last time it moved (dischargeOf), and
 *           Uplink: all the charge it has given up by moving since the
 *           reveal (uplinkOf)
 *
 *         The owner can change every setting until lock(), which is permanent.
 *         After a change, call the core's refreshAll() (or the owner's
 *         emitBatchMetadataUpdate) so marketplaces re-read the tokens.
 */
contract SeekerRenderer is ISeekerRenderer, TwoStepOwnable {
    using Strings for uint256;

    ISeekerNetCore public immutable core;

    uint256 public constant ART_COUNT = 2222;
    /// @notice The core's THRESHOLD and START_MAX (whole charge) and TAX_BPS.
    uint256 public constant THRESHOLD = 9000;
    uint256 public constant START_MAX = 8500;
    uint256 public constant TAX_BPS = 2500;
    /// @notice The core's RATE_PER_DAY and DAY.
    uint256 public constant RATE_PER_DAY = 50;
    uint256 public constant DAY = 86400;
    uint256 private constant ONE = 1e18;

    bool public locked;

    string public namePrefix = "SEEKER NET #";
    string public description;
    /// @notice Returned as-is before the reveal.
    string public unrevealedURI;
    string public dormantBase;
    string public activatedBase;
    string public dormantExt = ".png";
    string public activatedExt = ".gif";
    /// @notice true: image = base + artIndex + ext (one file per artwork).
    ///         false: image = base + ext, one image per state (rehearsal).
    bool public perArtImages = true;
    /// @notice Dormant stills per artwork (used with perArtImages).
    ///         1: image = dormantBase + artIndex + ext.
    ///         More: image = dormantBase + stage + "/" + artIndex + ext, with
    ///         stage 1..dormantStages, each covering an equal share of the
    ///         charge from 0 to THRESHOLD (see stageOf).
    uint256 public dormantStages = 6;
    /// @notice Optional link per token (e.g. a leaderboard page); empty = none.
    string public externalUrlBase;

    /// @notice Trait categories, e.g. Base, Colorway, Eyes, Floating Object,
    ///         Head, Flank, Back.
    string[] public categories;
    mapping(uint256 => string[]) internal _values;
    /// @notice SSTORE2 data: one byte per category per artwork, in artwork
    ///         order (value index into that category's names).
    address public traitData;

    /// @notice SSTORE2 data: two bytes (big-endian artwork index) per rank of
    ///         starting charge, lowest charge first; every artwork once.
    ///         0 = not set: tokens show the core's artIndexOf.
    address public chargeOrder;

    /// @notice Optional on-chain image per state (false = dormant, true =
    ///         activated), used when perArtImages is false: a complete data URI
    ///         ("data:image/gif;base64,...") stored in SSTORE2 chunks, so it
    ///         isn't re-encoded on every read. Empty = use the links.
    mapping(bool => address[]) internal _imageChunks;

    event SettingsUpdated();
    event Locked();

    error IsLocked();
    error BadTraitData();
    error BadCategory();
    error BadStages();
    error BadOrder();

    constructor(address core_) {
        core = ISeekerNetCore(core_);
    }

    modifier unlocked() {
        _checkOwner();
        if (locked) revert IsLocked();
        _;
        emit SettingsUpdated();
    }

    // ------------------------------------------------------------------
    // Owner settings
    // ------------------------------------------------------------------

    function setImages(
        string calldata dormantBase_,
        string calldata activatedBase_,
        string calldata dormantExt_,
        string calldata activatedExt_,
        bool perArtImages_
    ) external unlocked {
        dormantBase = dormantBase_;
        activatedBase = activatedBase_;
        dormantExt = dormantExt_;
        activatedExt = activatedExt_;
        perArtImages = perArtImages_;
    }

    function setDormantStages(uint256 stages) external unlocked {
        if (stages == 0 || stages > THRESHOLD) revert BadStages();
        dormantStages = stages;
    }

    function setTexts(
        string calldata namePrefix_,
        string calldata description_,
        string calldata unrevealedURI_,
        string calldata externalUrlBase_
    ) external unlocked {
        namePrefix = namePrefix_;
        description = description_;
        unrevealedURI = unrevealedURI_;
        externalUrlBase = externalUrlBase_;
    }

    /// @notice Replaces the on-chain image of one state with the first chunk
    ///         of its data URI (at most 24,575 bytes; empty clears it); add the
    ///         rest with addImageChunk. Only base64 data URIs belong here.
    function setOnchainImage(bool active, bytes calldata firstChunk)
        external
        unlocked
    {
        delete _imageChunks[active];
        if (firstChunk.length != 0) {
            _imageChunks[active].push(SSTORE2.write(firstChunk));
        }
    }

    function addImageChunk(bool active, bytes calldata chunk) external unlocked {
        _imageChunks[active].push(SSTORE2.write(chunk));
    }

    /// @notice Sets the category names; clears the trait data, whose layout
    ///         depends on them.
    function setCategories(string[] calldata names) external unlocked {
        delete categories;
        for (uint256 i; i < names.length; ++i) categories.push(names[i]);
        traitData = address(0);
    }

    function setValues(uint256 category, string[] calldata names)
        external
        unlocked
    {
        if (category >= categories.length) revert BadCategory();
        string[] storage v = _values[category];
        while (v.length != 0) v.pop();
        for (uint256 i; i < names.length; ++i) v.push(names[i]);
    }

    /// @param data categories.length bytes per artwork, ART_COUNT artworks.
    function setTraitData(bytes calldata data) external unlocked {
        uint256 n = categories.length;
        if (n == 0 || data.length != ART_COUNT * n) revert BadTraitData();
        uint256[] memory counts = new uint256[](n);
        for (uint256 k; k < n; ++k) counts[k] = _values[k].length;
        for (uint256 i; i < data.length; ++i) {
            if (uint8(data[i]) >= counts[i % n]) revert BadTraitData();
        }
        traitData = SSTORE2.write(data);
    }

    /// @param data two bytes per artwork (see chargeOrder); empty clears it.
    function setChargeOrder(bytes calldata data) external unlocked {
        if (data.length == 0) {
            chargeOrder = address(0);
            return;
        }
        if (data.length != ART_COUNT * 2) revert BadOrder();
        // every artwork exactly once
        uint256[] memory seen = new uint256[]((ART_COUNT + 255) / 256);
        for (uint256 i; i < ART_COUNT; ++i) {
            uint256 a = (uint256(uint8(data[2 * i])) << 8) |
                uint8(data[2 * i + 1]);
            if (a >= ART_COUNT) revert BadOrder();
            uint256 bit = 1 << (a & 255);
            if (seen[a >> 8] & bit != 0) revert BadOrder();
            seen[a >> 8] |= bit;
        }
        chargeOrder = SSTORE2.write(data);
    }

    /// @notice Freezes every setting for good.
    function lock() external unlocked {
        locked = true;
        emit Locked();
    }

    // ------------------------------------------------------------------
    // Views
    // ------------------------------------------------------------------

    /// @notice The on-chain image data URI of a state (empty if none).
    function onchainImage(bool active) public view returns (bytes memory out) {
        address[] storage c = _imageChunks[active];
        uint256 n = c.length;
        uint256 total;
        for (uint256 i; i < n; ++i) total += c[i].code.length - 1;
        out = new bytes(total);
        uint256 off;
        for (uint256 i; i < n; ++i) {
            address ptr = c[i];
            uint256 len = ptr.code.length - 1; // skip SSTORE2's leading STOP byte
            assembly {
                extcodecopy(ptr, add(add(out, 32), off), 1, len)
            }
            off += len;
        }
    }

    function values(uint256 category) external view returns (string[] memory) {
        return _values[category];
    }

    /// @notice The artwork's trait values (empty if no trait data is set).
    function traitsOf(uint256 artIndex)
        public
        view
        returns (string[] memory names, string[] memory vals)
    {
        address ptr = traitData;
        uint256 n = categories.length;
        if (ptr == address(0)) return (new string[](0), new string[](0));
        bytes memory raw = SSTORE2.read(ptr, artIndex * n, artIndex * n + n);
        names = new string[](n);
        vals = new string[](n);
        for (uint256 i; i < n; ++i) {
            names[i] = categories[i];
            vals[i] = _values[i][uint8(raw[i])];
        }
    }

    /// @notice Where a token's starting charge stands among the ART_COUNT
    ///         tokens (IDs 1..ART_COUNT): 0 = the lowest. Equal starting
    ///         charges are ordered by token ID. Fixed by the reveal seed.
    /// @dev    Recomputes the core's starting charges,
    ///         keccak256(seed, id) % (START_MAX + 1), for every token: about
    ///         300k gas, in a view.
    function chargeRankOf(uint256 id) public view returns (uint256 rank) {
        bytes32 seed = core.seed();
        uint256 m = START_MAX + 1;
        uint256 n = ART_COUNT;
        assembly {
            mstore(0x00, seed)
            mstore(0x20, id)
            let mine := mod(keccak256(0x00, 0x40), m)
            for {
                let j := 1
            } iszero(gt(j, n)) {
                j := add(j, 1)
            } {
                mstore(0x20, j)
                let s := mod(keccak256(0x00, 0x40), m)
                rank := add(
                    rank,
                    or(lt(s, mine), and(eq(s, mine), lt(j, id)))
                )
            }
        }
    }

    /// @notice Which artwork (row of the collection list, number of its image
    ///         files) a token shows. Reverts for missing tokens and before
    ///         the reveal.
    function artOf(uint256 id) public view returns (uint256) {
        uint256 art = core.artIndexOf(id);
        address ptr = chargeOrder;
        if (ptr == address(0)) return art;
        uint256 at = chargeRankOf(id) * 2;
        bytes memory b = SSTORE2.read(ptr, at, at + 2);
        return (uint256(uint8(b[0])) << 8) | uint8(b[1]);
    }

    /// @notice Which dormant still a charge (scaled by ONE) shows:
    ///         1..dormantStages. With six stages each covers 1,500 charge;
    ///         the last one runs up to and including THRESHOLD.
    function stageOf(uint256 charge) public view returns (uint256) {
        uint256 n = dormantStages;
        uint256 s = (charge * n) / (THRESHOLD * ONE);
        return s >= n ? n : s + 1;
    }

    /// @notice The charge (scaled by ONE) a dormant seeker gave up the last
    ///         time it moved: the 25% of its charge that went to the other
    ///         seekers. 0 if it hasn't moved since the reveal. Activated
    ///         seekers have none (0, and the trait is left out for them).
    /// @dev    A move keeps 75% of the charge, which is what the core stores;
    ///         the 25% given away is a third of that (to within the smallest
    ///         unit). Every later move replaces it, so moving a seeker back
    ///         and forth doesn't add up: the second move gives away 25% of
    ///         what the first one left.
    ///
    ///         Two cases read wrong, neither reachable in practice: a move
    ///         with nobody to share with (the last dormant seeker of all)
    ///         keeps everything but reads a third of it, and a seeker minted
    ///         after the reveal would read a third of its starting charge
    ///         (there are none: the supply was minted out before it).
    function dischargeOf(uint256 id) public view returns (uint256) {
        if (core.statusOf(id) != 0) return 0;
        (uint256 lastMove, , uint256 stored, ) = core.tokenState(id);
        if (lastMove == 0) return 0;
        return (stored * TAX_BPS) / (10_000 - TAX_BPS);
    }

    /// @notice All the charge (scaled by ONE) a dormant seeker has given up
    ///         by moving since the reveal: what it would have now had it never
    ///         moved, minus what it has. "Never moved" is the core's own
    ///         formula for an untouched seeker: its starting charge, plus
    ///         generation since the reveal, plus every share handed to each
    ///         dormant seeker since the reveal (accD). 0 if it hasn't moved.
    /// @dev    A move gives away 25% and, because the 25% is split among the
    ///         *other* seekers, also misses its own share of it; so this is
    ///         the moves' 25% plus those shares (1 / the number of other
    ///         dormant seekers at each move: about 0.05% with 2,221 of them).
    ///         Activated seekers have none (0, and the trait is left out for
    ///         them): recording an activation clears what this is worked out
    ///         from. Assumes every token was minted before the reveal, as all
    ///         ART_COUNT were.
    function uplinkOf(uint256 id) public view returns (uint256) {
        if (core.statusOf(id) != 0) return 0;
        (uint256 lastMove, , , ) = core.tokenState(id);
        if (lastMove == 0) return 0;
        uint256 reveal = core.revealTime();
        uint256 untouched = core.startChargeOf(id) +
            (
                block.timestamp > reveal
                    ? ((block.timestamp - reveal) * RATE_PER_DAY * ONE) / DAY
                    : 0
            ) +
            core.accD();
        uint256 c = core.chargeOf(id);
        return untouched > c ? untouched - c : 0;
    }

    function tokenURI(uint256 id) external view returns (string memory) {
        if (!core.isRevealed()) return unrevealedURI;
        return
            string.concat(
                "data:application/json;base64,",
                Base64.encode(bytes(tokenJSON(id)))
            );
    }

    /// @notice The metadata JSON itself (what tokenURI encodes).
    function tokenJSON(uint256 id) public view returns (string memory) {
        uint256 art = artOf(id); // reverts for missing tokens
        uint8 status = core.statusOf(id);
        bool active = status != 0;
        string memory image;
        if (!perArtImages && _imageChunks[active].length != 0) {
            image = string(onchainImage(active));
        } else {
            image = _esc(
                string.concat(
                    active ? activatedBase : dormantBase,
                    _imagePath(id, art, active),
                    active ? activatedExt : dormantExt
                )
            );
        }
        string memory ext = bytes(externalUrlBase).length == 0
            ? ""
            : string.concat(
                ',"external_url":"',
                _esc(externalUrlBase),
                id.toString(),
                '"'
            );
        return
            string.concat(
                '{"name":"',
                _esc(namePrefix),
                id.toString(),
                '","description":"',
                _esc(description),
                '","image":"',
                image,
                '"',
                ext,
                ',"attributes":',
                _attributes(id, art, status),
                "}"
            );
    }

    /// @dev What comes between the image folder and the extension.
    function _imagePath(
        uint256 id,
        uint256 art,
        bool active
    ) internal view returns (string memory) {
        if (!perArtImages) return "";
        // Files are named by artwork index, except artwork 0, whose files
        // are named ART_COUNT (the host's uploader can't take a file "0").
        string memory file = (art == 0 ? ART_COUNT : art).toString();
        if (active || dormantStages == 1) return file;
        return
            string.concat(stageOf(core.chargeOf(id)).toString(), "/", file);
    }

    function _attributes(
        uint256 id,
        uint256 art,
        uint8 status
    ) internal view returns (string memory out) {
        (string[] memory names, string[] memory vals) = traitsOf(art);
        out = "[";
        for (uint256 i; i < names.length; ++i) {
            out = string.concat(
                out,
                '{"trait_type":"',
                _esc(names[i]),
                '","value":"',
                _esc(vals[i]),
                '"},'
            );
        }
        out = string.concat(
            out,
            '{"trait_type":"Status","value":"',
            status != 0 ? "Activated" : "Dormant",
            '"},{"trait_type":"Charge","display_type":"number","value":',
            (core.chargeOf(id) / ONE).toString(),
            '},{"trait_type":"Starting Charge","display_type":"number","value":',
            (core.startChargeOf(id) / ONE).toString(),
            "}"
        );
        // Discharge and Uplink belong to seekers that are still charging
        if (status == 0) {
            out = string.concat(
                out,
                ',{"trait_type":"Discharge","display_type":"number","value":',
                (dischargeOf(id) / ONE).toString(),
                '},{"trait_type":"Uplink","display_type":"number","value":',
                (uplinkOf(id) / ONE).toString(),
                "}"
            );
        }
        out = string.concat(out, "]");
    }

    /// @dev JSON string escaping for owner-set text: quotes, backslashes and
    ///      newlines are escaped, other control characters dropped.
    function _esc(string memory s) internal pure returns (string memory) {
        bytes memory b = bytes(s);
        uint256 extra;
        for (uint256 i; i < b.length; ++i) {
            bytes1 c = b[i];
            if (c == '"' || c == "\\" || c == "\n") ++extra;
        }
        bool clean = extra == 0;
        for (uint256 i; clean && i < b.length; ++i) {
            if (uint8(b[i]) < 0x20) clean = false;
        }
        if (clean) return s;
        bytes memory o = new bytes(b.length + extra);
        uint256 j;
        for (uint256 i; i < b.length; ++i) {
            bytes1 c = b[i];
            if (c == '"' || c == "\\") {
                o[j++] = "\\";
                o[j++] = c;
            } else if (c == "\n") {
                o[j++] = "\\";
                o[j++] = "n";
            } else if (uint8(c) >= 0x20) {
                o[j++] = c;
            }
        }
        assembly {
            mstore(o, j)
        }
        return string(o);
    }
}
