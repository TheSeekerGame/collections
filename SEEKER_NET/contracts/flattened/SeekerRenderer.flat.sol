// SPDX-License-Identifier: MIT
pragma solidity =0.8.17 >=0.8.0 >=0.8.4 ^0.8.0;

// lib/openzeppelin-contracts/contracts/utils/Base64.sol

// OpenZeppelin Contracts (last updated v4.7.0) (utils/Base64.sol)

/**
 * @dev Provides a set of functions to operate with Base64 strings.
 *
 * _Available since v4.5._
 */
library Base64 {
    /**
     * @dev Base64 Encoding/Decoding Table
     */
    string internal constant _TABLE = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

    /**
     * @dev Converts a `bytes` to its Bytes64 `string` representation.
     */
    function encode(bytes memory data) internal pure returns (string memory) {
        /**
         * Inspired by Brecht Devos (Brechtpd) implementation - MIT licence
         * https://github.com/Brechtpd/base64/blob/e78d9fd951e7b0977ddca77d92dc85183770daf4/base64.sol
         */
        if (data.length == 0) return "";

        // Loads the table into memory
        string memory table = _TABLE;

        // Encoding takes 3 bytes chunks of binary data from `bytes` data parameter
        // and split into 4 numbers of 6 bits.
        // The final Base64 length should be `bytes` data length multiplied by 4/3 rounded up
        // - `data.length + 2`  -> Round up
        // - `/ 3`              -> Number of 3-bytes chunks
        // - `4 *`              -> 4 characters for each chunk
        string memory result = new string(4 * ((data.length + 2) / 3));

        /// @solidity memory-safe-assembly
        assembly {
            // Prepare the lookup table (skip the first "length" byte)
            let tablePtr := add(table, 1)

            // Prepare result pointer, jump over length
            let resultPtr := add(result, 32)

            // Run over the input, 3 bytes at a time
            for {
                let dataPtr := data
                let endPtr := add(data, mload(data))
            } lt(dataPtr, endPtr) {

            } {
                // Advance 3 bytes
                dataPtr := add(dataPtr, 3)
                let input := mload(dataPtr)

                // To write each character, shift the 3 bytes (18 bits) chunk
                // 4 times in blocks of 6 bits for each character (18, 12, 6, 0)
                // and apply logical AND with 0x3F which is the number of
                // the previous character in the ASCII table prior to the Base64 Table
                // The result is then added to the table to get the character to write,
                // and finally write it in the result pointer but with a left shift
                // of 256 (1 byte) - 8 (1 ASCII char) = 248 bits

                mstore8(resultPtr, mload(add(tablePtr, and(shr(18, input), 0x3F))))
                resultPtr := add(resultPtr, 1) // Advance

                mstore8(resultPtr, mload(add(tablePtr, and(shr(12, input), 0x3F))))
                resultPtr := add(resultPtr, 1) // Advance

                mstore8(resultPtr, mload(add(tablePtr, and(shr(6, input), 0x3F))))
                resultPtr := add(resultPtr, 1) // Advance

                mstore8(resultPtr, mload(add(tablePtr, and(input, 0x3F))))
                resultPtr := add(resultPtr, 1) // Advance
            }

            // When data `bytes` is not exactly 3 bytes long
            // it is padded with `=` characters at the end
            switch mod(mload(data), 3)
            case 1 {
                mstore8(sub(resultPtr, 1), 0x3d)
                mstore8(sub(resultPtr, 2), 0x3d)
            }
            case 2 {
                mstore8(sub(resultPtr, 1), 0x3d)
            }
        }

        return result;
    }
}

// lib/utility-contracts/src/ConstructorInitializable.sol

/**
 * @author emo.eth
 * @notice Abstract smart contract that provides an onlyUninitialized modifier which only allows calling when
 *         from within a constructor of some sort, whether directly instantiating an inherting contract,
 *         or when delegatecalling from a proxy
 */
abstract contract ConstructorInitializable {
    error AlreadyInitialized();

    modifier onlyConstructor() {
        if (address(this).code.length != 0) {
            revert AlreadyInitialized();
        }
        _;
    }
}

// src/ISeekerRenderer.sol

interface ISeekerRenderer {
    function tokenURI(uint256 tokenId) external view returns (string memory);
}

// lib/openzeppelin-contracts/contracts/utils/math/Math.sol

// OpenZeppelin Contracts (last updated v4.7.0) (utils/math/Math.sol)

/**
 * @dev Standard math utilities missing in the Solidity language.
 */
library Math {
    enum Rounding {
        Down, // Toward negative infinity
        Up, // Toward infinity
        Zero // Toward zero
    }

    /**
     * @dev Returns the largest of two numbers.
     */
    function max(uint256 a, uint256 b) internal pure returns (uint256) {
        return a > b ? a : b;
    }

    /**
     * @dev Returns the smallest of two numbers.
     */
    function min(uint256 a, uint256 b) internal pure returns (uint256) {
        return a < b ? a : b;
    }

    /**
     * @dev Returns the average of two numbers. The result is rounded towards
     * zero.
     */
    function average(uint256 a, uint256 b) internal pure returns (uint256) {
        // (a + b) / 2 can overflow.
        return (a & b) + (a ^ b) / 2;
    }

    /**
     * @dev Returns the ceiling of the division of two numbers.
     *
     * This differs from standard division with `/` in that it rounds up instead
     * of rounding down.
     */
    function ceilDiv(uint256 a, uint256 b) internal pure returns (uint256) {
        // (a + b - 1) / b can overflow on addition, so we distribute.
        return a == 0 ? 0 : (a - 1) / b + 1;
    }

    /**
     * @notice Calculates floor(x * y / denominator) with full precision. Throws if result overflows a uint256 or denominator == 0
     * @dev Original credit to Remco Bloemen under MIT license (https://xn--2-umb.com/21/muldiv)
     * with further edits by Uniswap Labs also under MIT license.
     */
    function mulDiv(
        uint256 x,
        uint256 y,
        uint256 denominator
    ) internal pure returns (uint256 result) {
        unchecked {
            // 512-bit multiply [prod1 prod0] = x * y. Compute the product mod 2^256 and mod 2^256 - 1, then use
            // use the Chinese Remainder Theorem to reconstruct the 512 bit result. The result is stored in two 256
            // variables such that product = prod1 * 2^256 + prod0.
            uint256 prod0; // Least significant 256 bits of the product
            uint256 prod1; // Most significant 256 bits of the product
            assembly {
                let mm := mulmod(x, y, not(0))
                prod0 := mul(x, y)
                prod1 := sub(sub(mm, prod0), lt(mm, prod0))
            }

            // Handle non-overflow cases, 256 by 256 division.
            if (prod1 == 0) {
                return prod0 / denominator;
            }

            // Make sure the result is less than 2^256. Also prevents denominator == 0.
            require(denominator > prod1);

            ///////////////////////////////////////////////
            // 512 by 256 division.
            ///////////////////////////////////////////////

            // Make division exact by subtracting the remainder from [prod1 prod0].
            uint256 remainder;
            assembly {
                // Compute remainder using mulmod.
                remainder := mulmod(x, y, denominator)

                // Subtract 256 bit number from 512 bit number.
                prod1 := sub(prod1, gt(remainder, prod0))
                prod0 := sub(prod0, remainder)
            }

            // Factor powers of two out of denominator and compute largest power of two divisor of denominator. Always >= 1.
            // See https://cs.stackexchange.com/q/138556/92363.

            // Does not overflow because the denominator cannot be zero at this stage in the function.
            uint256 twos = denominator & (~denominator + 1);
            assembly {
                // Divide denominator by twos.
                denominator := div(denominator, twos)

                // Divide [prod1 prod0] by twos.
                prod0 := div(prod0, twos)

                // Flip twos such that it is 2^256 / twos. If twos is zero, then it becomes one.
                twos := add(div(sub(0, twos), twos), 1)
            }

            // Shift in bits from prod1 into prod0.
            prod0 |= prod1 * twos;

            // Invert denominator mod 2^256. Now that denominator is an odd number, it has an inverse modulo 2^256 such
            // that denominator * inv = 1 mod 2^256. Compute the inverse by starting with a seed that is correct for
            // four bits. That is, denominator * inv = 1 mod 2^4.
            uint256 inverse = (3 * denominator) ^ 2;

            // Use the Newton-Raphson iteration to improve the precision. Thanks to Hensel's lifting lemma, this also works
            // in modular arithmetic, doubling the correct bits in each step.
            inverse *= 2 - denominator * inverse; // inverse mod 2^8
            inverse *= 2 - denominator * inverse; // inverse mod 2^16
            inverse *= 2 - denominator * inverse; // inverse mod 2^32
            inverse *= 2 - denominator * inverse; // inverse mod 2^64
            inverse *= 2 - denominator * inverse; // inverse mod 2^128
            inverse *= 2 - denominator * inverse; // inverse mod 2^256

            // Because the division is now exact we can divide by multiplying with the modular inverse of denominator.
            // This will give us the correct result modulo 2^256. Since the preconditions guarantee that the outcome is
            // less than 2^256, this is the final result. We don't need to compute the high bits of the result and prod1
            // is no longer required.
            result = prod0 * inverse;
            return result;
        }
    }

    /**
     * @notice Calculates x * y / denominator with full precision, following the selected rounding direction.
     */
    function mulDiv(
        uint256 x,
        uint256 y,
        uint256 denominator,
        Rounding rounding
    ) internal pure returns (uint256) {
        uint256 result = mulDiv(x, y, denominator);
        if (rounding == Rounding.Up && mulmod(x, y, denominator) > 0) {
            result += 1;
        }
        return result;
    }

    /**
     * @dev Returns the square root of a number. If the number is not a perfect square, the value is rounded down.
     *
     * Inspired by Henry S. Warren, Jr.'s "Hacker's Delight" (Chapter 11).
     */
    function sqrt(uint256 a) internal pure returns (uint256) {
        if (a == 0) {
            return 0;
        }

        // For our first guess, we get the biggest power of 2 which is smaller than the square root of the target.
        //
        // We know that the "msb" (most significant bit) of our target number `a` is a power of 2 such that we have
        // `msb(a) <= a < 2*msb(a)`. This value can be written `msb(a)=2**k` with `k=log2(a)`.
        //
        // This can be rewritten `2**log2(a) <= a < 2**(log2(a) + 1)`
        // → `sqrt(2**k) <= sqrt(a) < sqrt(2**(k+1))`
        // → `2**(k/2) <= sqrt(a) < 2**((k+1)/2) <= 2**(k/2 + 1)`
        //
        // Consequently, `2**(log2(a) / 2)` is a good first approximation of `sqrt(a)` with at least 1 correct bit.
        uint256 result = 1 << (log2(a) >> 1);

        // At this point `result` is an estimation with one bit of precision. We know the true value is a uint128,
        // since it is the square root of a uint256. Newton's method converges quadratically (precision doubles at
        // every iteration). We thus need at most 7 iteration to turn our partial result with one bit of precision
        // into the expected uint128 result.
        unchecked {
            result = (result + a / result) >> 1;
            result = (result + a / result) >> 1;
            result = (result + a / result) >> 1;
            result = (result + a / result) >> 1;
            result = (result + a / result) >> 1;
            result = (result + a / result) >> 1;
            result = (result + a / result) >> 1;
            return min(result, a / result);
        }
    }

    /**
     * @notice Calculates sqrt(a), following the selected rounding direction.
     */
    function sqrt(uint256 a, Rounding rounding) internal pure returns (uint256) {
        unchecked {
            uint256 result = sqrt(a);
            return result + (rounding == Rounding.Up && result * result < a ? 1 : 0);
        }
    }

    /**
     * @dev Return the log in base 2, rounded down, of a positive value.
     * Returns 0 if given 0.
     */
    function log2(uint256 value) internal pure returns (uint256) {
        uint256 result = 0;
        unchecked {
            if (value >> 128 > 0) {
                value >>= 128;
                result += 128;
            }
            if (value >> 64 > 0) {
                value >>= 64;
                result += 64;
            }
            if (value >> 32 > 0) {
                value >>= 32;
                result += 32;
            }
            if (value >> 16 > 0) {
                value >>= 16;
                result += 16;
            }
            if (value >> 8 > 0) {
                value >>= 8;
                result += 8;
            }
            if (value >> 4 > 0) {
                value >>= 4;
                result += 4;
            }
            if (value >> 2 > 0) {
                value >>= 2;
                result += 2;
            }
            if (value >> 1 > 0) {
                result += 1;
            }
        }
        return result;
    }

    /**
     * @dev Return the log in base 2, following the selected rounding direction, of a positive value.
     * Returns 0 if given 0.
     */
    function log2(uint256 value, Rounding rounding) internal pure returns (uint256) {
        unchecked {
            uint256 result = log2(value);
            return result + (rounding == Rounding.Up && 1 << result < value ? 1 : 0);
        }
    }

    /**
     * @dev Return the log in base 10, rounded down, of a positive value.
     * Returns 0 if given 0.
     */
    function log10(uint256 value) internal pure returns (uint256) {
        uint256 result = 0;
        unchecked {
            if (value >= 10**64) {
                value /= 10**64;
                result += 64;
            }
            if (value >= 10**32) {
                value /= 10**32;
                result += 32;
            }
            if (value >= 10**16) {
                value /= 10**16;
                result += 16;
            }
            if (value >= 10**8) {
                value /= 10**8;
                result += 8;
            }
            if (value >= 10**4) {
                value /= 10**4;
                result += 4;
            }
            if (value >= 10**2) {
                value /= 10**2;
                result += 2;
            }
            if (value >= 10**1) {
                result += 1;
            }
        }
        return result;
    }

    /**
     * @dev Return the log in base 10, following the selected rounding direction, of a positive value.
     * Returns 0 if given 0.
     */
    function log10(uint256 value, Rounding rounding) internal pure returns (uint256) {
        unchecked {
            uint256 result = log10(value);
            return result + (rounding == Rounding.Up && 10**result < value ? 1 : 0);
        }
    }

    /**
     * @dev Return the log in base 256, rounded down, of a positive value.
     * Returns 0 if given 0.
     *
     * Adding one to the result gives the number of pairs of hex symbols needed to represent `value` as a hex string.
     */
    function log256(uint256 value) internal pure returns (uint256) {
        uint256 result = 0;
        unchecked {
            if (value >> 128 > 0) {
                value >>= 128;
                result += 16;
            }
            if (value >> 64 > 0) {
                value >>= 64;
                result += 8;
            }
            if (value >> 32 > 0) {
                value >>= 32;
                result += 4;
            }
            if (value >> 16 > 0) {
                value >>= 16;
                result += 2;
            }
            if (value >> 8 > 0) {
                result += 1;
            }
        }
        return result;
    }

    /**
     * @dev Return the log in base 10, following the selected rounding direction, of a positive value.
     * Returns 0 if given 0.
     */
    function log256(uint256 value, Rounding rounding) internal pure returns (uint256) {
        unchecked {
            uint256 result = log256(value);
            return result + (rounding == Rounding.Up && 1 << (result * 8) < value ? 1 : 0);
        }
    }
}

// lib/solmate/src/utils/SSTORE2.sol

/// @notice Read and write to persistent storage at a fraction of the cost.
/// @author Solmate (https://github.com/transmissions11/solmate/blob/main/src/utils/SSTORE2.sol)
/// @author Modified from 0xSequence (https://github.com/0xSequence/sstore2/blob/master/contracts/SSTORE2.sol)
library SSTORE2 {
    uint256 internal constant DATA_OFFSET = 1; // We skip the first byte as it's a STOP opcode to ensure the contract can't be called.

    /*//////////////////////////////////////////////////////////////
                               WRITE LOGIC
    //////////////////////////////////////////////////////////////*/

    function write(bytes memory data) internal returns (address pointer) {
        // Prefix the bytecode with a STOP opcode to ensure it cannot be called.
        bytes memory runtimeCode = abi.encodePacked(hex"00", data);

        bytes memory creationCode = abi.encodePacked(
            //---------------------------------------------------------------------------------------------------------------//
            // Opcode  | Opcode + Arguments  | Description  | Stack View                                                     //
            //---------------------------------------------------------------------------------------------------------------//
            // 0x60    |  0x600B             | PUSH1 11     | codeOffset                                                     //
            // 0x59    |  0x59               | MSIZE        | 0 codeOffset                                                   //
            // 0x81    |  0x81               | DUP2         | codeOffset 0 codeOffset                                        //
            // 0x38    |  0x38               | CODESIZE     | codeSize codeOffset 0 codeOffset                               //
            // 0x03    |  0x03               | SUB          | (codeSize - codeOffset) 0 codeOffset                           //
            // 0x80    |  0x80               | DUP          | (codeSize - codeOffset) (codeSize - codeOffset) 0 codeOffset   //
            // 0x92    |  0x92               | SWAP3        | codeOffset (codeSize - codeOffset) 0 (codeSize - codeOffset)   //
            // 0x59    |  0x59               | MSIZE        | 0 codeOffset (codeSize - codeOffset) 0 (codeSize - codeOffset) //
            // 0x39    |  0x39               | CODECOPY     | 0 (codeSize - codeOffset)                                      //
            // 0xf3    |  0xf3               | RETURN       |                                                                //
            //---------------------------------------------------------------------------------------------------------------//
            hex"60_0B_59_81_38_03_80_92_59_39_F3", // Returns all code in the contract except for the first 11 (0B in hex) bytes.
            runtimeCode // The bytecode we want the contract to have after deployment. Capped at 1 byte less than the code size limit.
        );

        assembly {
            // Deploy a new contract with the generated creation code.
            // We start 32 bytes into the code to avoid copying the byte length.
            pointer := create(0, add(creationCode, 32), mload(creationCode))
        }

        require(pointer != address(0), "DEPLOYMENT_FAILED");
    }

    /*//////////////////////////////////////////////////////////////
                               READ LOGIC
    //////////////////////////////////////////////////////////////*/

    function read(address pointer) internal view returns (bytes memory) {
        return readBytecode(pointer, DATA_OFFSET, pointer.code.length - DATA_OFFSET);
    }

    function read(address pointer, uint256 start) internal view returns (bytes memory) {
        start += DATA_OFFSET;

        return readBytecode(pointer, start, pointer.code.length - start);
    }

    function read(
        address pointer,
        uint256 start,
        uint256 end
    ) internal view returns (bytes memory) {
        start += DATA_OFFSET;
        end += DATA_OFFSET;

        require(pointer.code.length >= end, "OUT_OF_BOUNDS");

        return readBytecode(pointer, start, end - start);
    }

    /*//////////////////////////////////////////////////////////////
                          INTERNAL HELPER LOGIC
    //////////////////////////////////////////////////////////////*/

    function readBytecode(
        address pointer,
        uint256 start,
        uint256 size
    ) private view returns (bytes memory data) {
        assembly {
            // Get a pointer to some free memory.
            data := mload(0x40)

            // Update the free memory pointer to prevent overriding our data.
            // We use and(x, not(31)) as a cheaper equivalent to sub(x, mod(x, 32)).
            // Adding 31 to size and running the result through the logic above ensures
            // the memory pointer remains word-aligned, following the Solidity convention.
            mstore(0x40, add(data, and(add(add(size, 32), 31), not(31))))

            // Store the size of the data in the first 32 byte chunk of free memory.
            mstore(data, size)

            // Copy the code into memory right after the 32 bytes we used to store the size.
            extcodecopy(pointer, add(data, 32), start, size)
        }
    }
}

// lib/openzeppelin-contracts/contracts/utils/Strings.sol

// OpenZeppelin Contracts (last updated v4.7.0) (utils/Strings.sol)

/**
 * @dev String operations.
 */
library Strings {
    bytes16 private constant _SYMBOLS = "0123456789abcdef";
    uint8 private constant _ADDRESS_LENGTH = 20;

    /**
     * @dev Converts a `uint256` to its ASCII `string` decimal representation.
     */
    function toString(uint256 value) internal pure returns (string memory) {
        unchecked {
            uint256 length = Math.log10(value) + 1;
            string memory buffer = new string(length);
            uint256 ptr;
            /// @solidity memory-safe-assembly
            assembly {
                ptr := add(buffer, add(32, length))
            }
            while (true) {
                ptr--;
                /// @solidity memory-safe-assembly
                assembly {
                    mstore8(ptr, byte(mod(value, 10), _SYMBOLS))
                }
                value /= 10;
                if (value == 0) break;
            }
            return buffer;
        }
    }

    /**
     * @dev Converts a `uint256` to its ASCII `string` hexadecimal representation.
     */
    function toHexString(uint256 value) internal pure returns (string memory) {
        unchecked {
            return toHexString(value, Math.log256(value) + 1);
        }
    }

    /**
     * @dev Converts a `uint256` to its ASCII `string` hexadecimal representation with fixed length.
     */
    function toHexString(uint256 value, uint256 length) internal pure returns (string memory) {
        bytes memory buffer = new bytes(2 * length + 2);
        buffer[0] = "0";
        buffer[1] = "x";
        for (uint256 i = 2 * length + 1; i > 1; --i) {
            buffer[i] = _SYMBOLS[value & 0xf];
            value >>= 4;
        }
        require(value == 0, "Strings: hex length insufficient");
        return string(buffer);
    }

    /**
     * @dev Converts an `address` with fixed length of 20 bytes to its not checksummed ASCII `string` hexadecimal representation.
     */
    function toHexString(address addr) internal pure returns (string memory) {
        return toHexString(uint256(uint160(addr)), _ADDRESS_LENGTH);
    }
}

// lib/utility-contracts/src/TwoStepOwnable.sol

/**
@notice A two-step extension of Ownable, where the new owner must claim ownership of the contract after owner initiates transfer
Owner can cancel the transfer at any point before the new owner claims ownership.
Helpful in guarding against transferring ownership to an address that is unable to act as the Owner.
*/
abstract contract TwoStepOwnable is ConstructorInitializable {
    address private _owner;

    event OwnershipTransferred(
        address indexed previousOwner,
        address indexed newOwner
    );

    address internal potentialOwner;

    event PotentialOwnerUpdated(address newPotentialAdministrator);

    error NewOwnerIsZeroAddress();
    error NotNextOwner();
    error OnlyOwner();

    modifier onlyOwner() {
        _checkOwner();
        _;
    }

    constructor() {
        _initialize();
    }

    function _initialize() private onlyConstructor {
        _transferOwnership(msg.sender);
    }

    ///@notice Initiate ownership transfer to newPotentialOwner. Note: new owner will have to manually acceptOwnership
    ///@param newPotentialOwner address of potential new owner
    function transferOwnership(address newPotentialOwner)
        public
        virtual
        onlyOwner
    {
        if (newPotentialOwner == address(0)) {
            revert NewOwnerIsZeroAddress();
        }
        potentialOwner = newPotentialOwner;
        emit PotentialOwnerUpdated(newPotentialOwner);
    }

    ///@notice Claim ownership of smart contract, after the current owner has initiated the process with transferOwnership
    function acceptOwnership() public virtual {
        address _potentialOwner = potentialOwner;
        if (msg.sender != _potentialOwner) {
            revert NotNextOwner();
        }
        delete potentialOwner;
        emit PotentialOwnerUpdated(address(0));
        _transferOwnership(_potentialOwner);
    }

    ///@notice cancel ownership transfer
    function cancelOwnershipTransfer() public virtual onlyOwner {
        delete potentialOwner;
        emit PotentialOwnerUpdated(address(0));
    }

    function owner() public view virtual returns (address) {
        return _owner;
    }

    /**
     * @dev Throws if the sender is not the owner.
     */
    function _checkOwner() internal view virtual {
        if (_owner != msg.sender) {
            revert OnlyOwner();
        }
    }

    /**
     * @dev Leaves the contract without owner. It will not be possible to call
     * `onlyOwner` functions anymore. Can only be called by the current owner.
     *
     * NOTE: Renouncing ownership will leave the contract without an owner,
     * thereby removing any functionality that is only available to the owner.
     */
    function renounceOwnership() public virtual onlyOwner {
        _transferOwnership(address(0));
    }

    /**
     * @dev Transfers ownership of the contract to a new account (`newOwner`).
     * Internal function without access restriction.
     */
    function _transferOwnership(address newOwner) internal virtual {
        address oldOwner = _owner;
        _owner = newOwner;
        emit OwnershipTransferred(oldOwner, newOwner);
    }
}

// src/SeekerRenderer.sol

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

