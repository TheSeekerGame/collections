# SEEKER NET: complete archive

Everything needed to re-draw any seeker:

- every layer the art is built from, still and animated
- lists of all 2,222 tokens, each with its traits and the exact layer files it uses
- `seeker.py`, which draws any token from the layers: still or animated, uncharged or activated, at any charge, or at its live charge read from the chain
- `live.py`, which reads every token's live status, charge, picture, Discharge and Uplink from the chain, for games (see [Live data for games](#live-data-for-games))

The finished art itself (2,222 activated GIFs and 13,332 uncharged pictures) is not in this folder: any of it
can be drawn from the layers in seconds, and all of it is on Arweave (links below).

> **Built for making things quickly, including with AI agents.** Everything here is ready to use as it is:
> take the layers, the lists and `seeker.py` and start building. All checking and verification described below
> (`--check`, `verify.py`, the checksums in the lists) is **entirely optional**. The art has already been
> verified, so there is no need to re-verify anything before using it, and an agent should skip these steps
> unless it is specifically asked to check something.

## Contents

| Path | What it is |
|---|---|
| `README.md` | this file |
| `seeker.py` | draws any token from the layers (see [Drawing a token](#drawing-a-token)) |
| `live.py` | reads every token's live state from public RPCs (see [Live data for games](#live-data-for-games)) |
| `verify.py` | optional: re-draws the whole collection from the layers and checks it against the checksums |
| `requirements.txt` | the two Python packages the scripts need |
| `layers/` | every layer (see [The layers](#the-layers)) |
| `lists/tokens.csv` / `.json` | one row per token ID (1 to 2,222): its seeker, traits, starting charge, every layer file it uses and its art on Arweave |
| `lists/artworks.csv` / `.json` | the same rows ordered by artwork number (0 to 2,221) |
| `lists/provenance.txt` | the collection list, hashed and posted publicly before the reveal |
| `lists/provenance_hash.txt` | that hash |
| `engine/` | the code that drew the collection (used by the scripts) |
| `contracts/` | the two smart contracts: the SEEKER NET collection and its renderer (see [The contracts](#the-contracts)) |

## The collection

| | |
|---|---|
| Contract | SEEKER NET, `0x5aC790269A6c71a51Ba68BF6a3a2647F86788792` |
| Chain | Robinhood Chain (chain ID 4663), RPC `https://rpc.mainnet.chain.robinhood.com` |
| Supply | 2,222 tokens, IDs 1 to 2,222 |
| Reveal seed | `0x6272177d4a8e31b34e35fd072f92d5a40f006c7fa9acecd549bb3bbe17a1b2c3` |
| List hash | `0x916ed1c07b66f369dde80cc51f032dedd1a5e03cc3a01d7ce222c2b7b467ba10` (keccak256 of `lists/provenance.txt`) |
| Activated GIFs on Arweave | `https://arweave.net/4vC6crUf-ZrzM9CbosRIwDxbt_bDRypYuqz6sveAIKo/<file number>.gif` |
| Uncharged pictures on Arweave | `https://arweave.net/hdiSRFBqjEfJIuN_M8DNXDc2yfQjh56JpKwxoY7iYDY/<stage>/<file number>.png` |

### Artwork numbers and file numbers

There are 2,222 artworks, numbered 0 to 2,221 (the row in the collection list). Their files are named by
**file number**, which is the artwork number, except that artwork 0's files are named **2222**. So the files
run from `1.gif` to `2222.gif`, and `2222.gif` is artwork 0. Every list gives both numbers.

### Which token shows which seeker

Fixed at the reveal by the seed, and the same rule the contract uses:

1. Every token gets a starting charge: `keccak256(abi.encode(seed, tokenId)) % 8501`.
2. The tokens are put in order of starting charge, lowest first (equal charges: lower token ID first).
3. The token in place *k* of that order shows the seeker with **Charge Rank** *k* in the collection
   list. Charge Rank 0 is the rarest seeker, so **the rarer the seeker, the lower its starting charge**.

`lists/tokens.csv` has the result for every token, so you never need to work this out yourself.

### What a token shows

A seeker is **uncharged** until its charge goes over 9,000, then **activated** for good.

| Charge | Picture |
|---|---|
| 0 to 1,499 | uncharged, stage 1 (darkest, emptiest battery) |
| 1,500 to 2,999 | uncharged, stage 2 |
| 3,000 to 4,499 | uncharged, stage 3 |
| 4,500 to 5,999 | uncharged, stage 4 |
| 6,000 to 7,499 | uncharged, stage 5 |
| 7,500 to 9,000 | uncharged, stage 6 (brightest, full battery) |
| over 9,000 | activated: the animated GIF |

Uncharged pictures show a battery on the screen instead of the eyes, the seeker darkened by the stage's shade,
on the uncharged background. Activated GIFs show the seeker with its eyes, moving, on its own Background.

## How SEEKER NET works

SEEKER NET is a game played entirely by the collection's smart contract. There is no server and nobody runs
it: every seeker's charge is worked out on-chain from time and from transfers, and its picture and traits follow
from its charge. The rules are fixed in the contract and can never change.

### The goal: charge over 9,000

Every seeker has a **charge**. A seeker starts **uncharged** (a dark, still picture with a battery on its
screen). The moment its charge goes over 9,000 it is **activated**: it comes alive as an animated GIF, for good.

### Uncharged seekers

1. **Starting charge.** At the reveal every seeker got a random starting charge from 0 to 8,500. The rarer the
   seeker, the lower its starting charge (see [Which token shows which seeker](#which-token-shows-which-seeker)).
2. **Charging.** Every seeker gains **50 charge a day**, continuously (a little every second), whether or not
   anyone does anything.
3. **Moving costs charge, and pays everyone else.** When a seeker moves (any transfer: a sale, a gift, a move
   between your own wallets), it keeps **75%** of its charge and the other **25% is split equally among all the
   other uncharged seekers**. So every move by someone else adds a little to your seeker, and moving your own
   costs it a quarter. If no other uncharged seeker is left, a move costs nothing.
4. **Activation.** When a seeker's charge goes over 9,000 it is activated. Its picture becomes the animated GIF
   straight away, and it never goes back.

With no moves at all, a seeker at 0 would take 180 days to reach 9,000. In practice it is quicker, because every
other seeker's moves add to it.

### Activated seekers

5. **Recording.** An activation is written into the contract the first time the seeker is touched afterwards:
   when anyone calls `activate` (or `activateMany`) for it, or when it moves. At that moment its charge is set
   to exactly 9,000. Charge collected between going over 9,000 and being recorded is not kept, so recording
   early is best. Until it is recorded, an activated seeker shows a charge of 9,000.
6. **A second race above 9,000.** Recorded activated seekers keep gaining 50 a day, and receive charge only from
   other activated seekers, never from uncharged ones.
7. **Moving an activated seeker** keeps 75% of its charge *above 9,000*; the other 25% of that is split among
   the other recorded activated seekers. It never drops below 9,000.

### General rules

- The game started at the reveal (12 October 2026, 23:13 UTC); transfers before it did nothing.
- Charge is kept to 18 decimal places; the traits show it as a whole number.
- A burned token leaves the game.
- The rules (50 a day, starting charge 0 to 8,500, 25% on a move, activation over 9,000) are fixed in the
  contract and cannot be changed by anyone.

### The traits

Every token's metadata is built on-chain, live, by the renderer contract:

| Trait | Meaning |
|---|---|
| Base, Colorway, Eyes, Floating Object, Head, Flank, Back, Background | the seeker's look; they never change |
| Loadout | how much the seeker carries; this is its rarity: Bare (32, rarest), Fully Loaded (56), Light (302), Heavy (712), Standard (1,120) |
| Status | `Dormant` (uncharged) or `Activated` |
| Charge | its charge right now, whole number |
| Starting Charge | its charge at the reveal |
| Discharge | uncharged seekers only: the charge it gave up in its last move (0 if it never moved) |
| Uplink | uncharged seekers only: all the charge it has given up in every move since the reveal |

Marketplaces don't notice a charge change by themselves; they re-read a token when it moves, or when anyone
sends the contract's refresh signal (`refreshTokens`, free for anyone apart from gas).

### The rarity order (Charge Rank)

Charge Rank 0 to 2,221 orders the seekers from rarest to most common, and was fixed in `lists/provenance.txt`
before the reveal:

1. by Loadout, the smallest group first: Bare, Fully Loaded, Light, Heavy, Standard
2. inside a Loadout, the seeker whose trait values are shared by the fewest seekers of that Loadout first (the
   product of those counts over Base, Colorway, Eyes, Floating Object, Head, Flank, Back and Background)
3. still equal: by the sha256 of the seeker's line in the list

## The contracts

`contracts/` holds the source code of both contracts. The code deployed on-chain was compiled from exactly
these files (checked byte for byte against the chain).

| Contract | Address | File |
|---|---|---|
| SEEKER NET (the collection and the game) | `0x5aC790269A6c71a51Ba68BF6a3a2647F86788792` | `contracts/src/SeekerNet.sol` |
| Renderer (metadata, pictures and traits) | `0x83C8AA41d5b45F05AdFE2f4259E290c31e79Cd2D` | `contracts/src/SeekerRenderer.sol` |

- **SEEKER NET** is OpenSea's standard drop contract (ERC721SeaDrop) plus the charge game. Its game rules can
  never change.
- **The renderer** turns a token's on-chain state into its metadata: which seeker it shows, the picture for its
  charge and its traits. The owner can replace it (that is how the Uplink trait was added), until it is locked
  for good. As of October 2026 it is not locked.
- `contracts/src/ISeekerRenderer.sol` is the small interface between the two.
- `contracts/flattened/` has each contract as one file with all the library code it uses (OpenSea SeaDrop,
  OpenZeppelin, solmate, ERC721A), so it can be read or compiled on its own.
- `contracts/abi/` has the ABI of each contract, for calling them from code.

Compiler settings: Solidity 0.8.17, optimizer on with 200 runs, EVM version cancun, no metadata hash.

Useful read-only functions (free to call, no wallet needed):

| Contract | Function | Answer |
|---|---|---|
| SEEKER NET | `chargeOf(id)` | charge now, with 18 decimals (divide by 10^18) |
| SEEKER NET | `statusOf(id)` | 0 uncharged, 1 activated but not recorded yet, 2 activated, 3 no such token |
| SEEKER NET | `startChargeOf(id)` | starting charge, 18 decimals |
| SEEKER NET | `chargesOf(from, to)` | charges and statuses of a range of tokens at once |
| SEEKER NET | `tokenState(id)` | the raw stored state (last move time, share snapshot, stored charge, recorded) |
| SEEKER NET | `seed()`, `revealTime()`, `activatedCount()` | the reveal seed, when the game started, how many activations are recorded |
| SEEKER NET | `tokenURI(id)` | the full metadata, as built by the renderer |
| Renderer | `artOf(id)` | which artwork (0 to 2,221) the token shows. Use this one: SEEKER NET's own `artIndexOf` is an older mapping the renderer replaces |
| Renderer | `tokenJSON(id)` | the metadata JSON as plain text |
| Renderer | `stageOf(charge)` | the uncharged picture stage for a charge (18 decimals) |
| Renderer | `dischargeOf(id)`, `uplinkOf(id)` | the Discharge and Uplink values, 18 decimals |

Anyone can also send `activate(id)` / `activateMany(ids)` (record activations) and `refreshTokens(from, to)`
(ask marketplaces to re-read tokens); each costs only gas.

## The layers

Everything is 54 x 54 pixels. The collection's art is the same pictures scaled up 20 times with no smoothing
(1,080 pixels).

| Folder | Contents |
|---|---|
| `layers/bases/` | the 16 monitors (Base trait) |
| `layers/eyes/` | the 32 eyes (Eyes trait) |
| `layers/objects/` | the 14 floating objects (Floating Object trait) |
| `layers/head/` | the 10 hats (Head trait) |
| `layers/flank/` | the 7 side add-ons (Flank trait) |
| `layers/back/` | the 7 back add-ons (Back trait) |
| `layers/backgrounds/` | the 8 backgrounds of activated seekers (Background trait) |
| `layers/uncharged/` | for uncharged seekers: `background.png`, `battery1-6.png` (the battery shown on the screen at each stage) and `shade1-6.png` (the darkening at each stage) |
| `layers/animated/` | the animated version of every monitor, eye and add-on (see below) |
| `layers/colorways.json` / `.png` | the 20 colorways |
| `layers/all_colours_palette_labelled.png` / `.txt` | every colour used anywhere in the collection |

Each file is named after its trait, for example `layers/head/Propeller.png`.

**How a seeker is put together.** Every monitor and add-on was painted by the artist on the Classic monitor,
in one master set of colours. To draw a seeker:

1. **Colours.** Six colour roles (lid, front body, body shadow, screen-inset shadow, secondary plate, indicator
   light) are swapped from the master colours to the seeker's Colorway (`layers/colorways.json`). Other
   colours, like rim lights and screen glass, are the same on every seeker.
2. **Placement.** Add-ons are moved from the Classic onto the seeker's own monitor by fixed rules: the hat
   stands on the lid, the back add-on follows the back edge of the lid and hides behind the body, the flank
   add-ons keep their gap to the sides, the floating object is centred under the front, and the eyes are
   centred on the open part of the screen. The whole picture then shifts the least needed to fit the round
   profile-picture crop. The rules are in `engine/final.py`.
3. **Paint order**, back to front: floating object, back add-on, monitor, flank add-on, hat, eyes.

**Animated layers.** `layers/animated/<slot>/<trait>.png` is a strip of frames, each an 86 x 86 cell (the
54 x 54 canvas with 16 pixels of margin so motion can leave it), with a `.json` file next to it describing the
motion. The engine combines them into a GIF: one frame per 50 ms, 72 frames (3.6 s) or, for a seeker with two
big motions, 96 frames (4.8 s). The first frame of every GIF is the seeker at rest.

## The lists

`lists/tokens.csv` (and `.json`) has one row per token. Columns:

| Column | Meaning |
|---|---|
| `token` | token ID, 1 to 2,222 |
| `artwork`, `file_number` | the seeker it shows (see above) |
| `Base` to `Loadout` | its traits (`None` = empty slot) |
| `charge_rank` | place in the rarity order, 0 = rarest |
| `starting_charge` | its charge at the reveal, 0 to 8,500 |
| `base_layer` to `background_layer` | the layer files it is drawn from (empty = slot not used) |
| `animated_base` to `animated_back` | the animated layer files of its activated GIF |
| `arweave_activated`, `arweave_uncharged` | its finished art on Arweave (`<stage>` = 1 to 6) |
| `activated_pixels_sha256` | checksum of its activated GIF's pixels: every frame, 54 x 54 |
| `activated_still_pixels_sha256` | checksum of the GIF's first frame (the seeker at rest) |
| `uncharged_stage_1_pixels_sha256` to `..._6_...` | checksums of its six uncharged pictures |

The checksum columns are only for optional checking; you can ignore them. A pixel checksum is the sha256 of the picture's 54 x 54 RGB pixels, frame after frame (one frame every 50 ms
for a GIF). It does not depend on how a file was compressed, so a fresh drawing can be compared with the
collection even though its file bytes differ.

Every uncharged picture also uses the files in `layers/uncharged/`, and every seeker's colours come from
`layers/colorways.json`; those are the same for all rows, so they are not repeated in the lists.
`lists/artworks.csv` has the same rows in artwork order, plus an `index` column (the artwork number again,
which the engine reads).

## Drawing a token

You need Python 3.9 or newer, then once:

```
pip3 install -r requirements.txt
```

Then, from this folder:

```
python3 seeker.py 1895                       # what token 1895 shows right now (reads its charge from the chain)
python3 seeker.py 1895 --charge 4200         # as an uncharged seeker at 4,200 charge
python3 seeker.py 1895 --charge 9500         # activated: the animated GIF
python3 seeker.py 1895 --activated           # the same, without giving a charge
python3 seeker.py 1895 --activated --still   # activated, as a still picture (the GIF's first frame)
python3 seeker.py 1895 --info                # print its traits, live charge and files; draw nothing
python3 seeker.py 1895 --check               # optional: also compare with the collection's checksum
python3 seeker.py --artwork 716 --charge 0   # by artwork number instead of token ID
```

| Option | |
|---|---|
| `--charge N` | the charge to draw it at. 0 to 9,000 gives the uncharged picture for that stage; above 9,000 gives the activated GIF |
| `--activated` | draw the activated version, whatever the charge |
| `--still` | with an activated seeker: a still PNG instead of the GIF |
| `--scale N` | pixels per art pixel. 20 (default) = 1,080 x 1,080 like the collection; 1 = 54 x 54; 40 = 2,160 x 2,160 |
| `--out FILE` | where to save it. Default: `renders/token-<id>-<state>.png` or `.gif` |
| `--rpc URL` | a different Robinhood Chain RPC for reading the live charge |
| `--info` | print the details only |
| `--check` | optional: also compare the drawing with the collection's pixel checksum |

**Live charge.** Without `--charge` or `--activated`, the script asks the SEEKER NET contract for the token's
current charge and status (`chargeOf` and `statusOf`). It is a free, read-only call over the internet; no
wallet or key is involved. A token whose charge is over 9,000 is drawn activated, even before its activation is
recorded on-chain.

The script prints what it is drawing, for example:

```
SEEKER NET #1895
  artwork 1613 (file number 1613)
  Base: Handheld · Colorway: Tide · Eyes: Wide · Floating Object: Classic Keyboard · Head: None · ...
  starting charge 6976 · Charge Rank 1842 (0 = rarest)
  charge 2,077.80 (live, read from the chain): uncharged, picture stage 2 of 6
  layers: layers/bases/Handheld.png, layers/eyes/Wide.png, layers/objects/Classic Keyboard.png, ...
  wrote renders/token-1895-uncharged-stage2.png
```

## Live data for games

Every changing value of a seeker is worked out by the contract itself, so every game that reads the chain shows
the same seeker at the same moment, single-player games included. No server of ours is involved: a game reads a
public Robinhood Chain RPC directly.

### What changes

| | Changes | Read it from |
|---|---|---|
| Base to Background, Loadout, artwork, starting charge | never | `lists/tokens.csv` |
| Charge | all the time: 50 a day, plus a share of every other seeker's move, minus 25% on its own moves | `chargeOf`, `chargesOf` |
| Status | once: Dormant until the charge reaches 9,000, then Activated (recorded later, see [Activated seekers](#activated-seekers)) | `statusOf`, `chargesOf` |
| Picture | with the status, and while dormant with the stage (every 1,500 charge) | charge and status, see [What a token shows](#what-a-token-shows) |
| Discharge, Uplink | only when the seeker itself moves | the renderer's `dischargeOf`, `uplinkOf` |
| Renderer | if the owner replaces it, until it is locked | `renderer()` on SEEKER NET |

### Public APIs

As tested on 17 October 2026:

| API | Key | Browser games (CORS) | Notes |
|---|---|---|---|
| `https://rpc.mainnet.chain.robinhood.com` | none | yes | Robinhood's public RPC. Rate-limited, with no published numbers; Robinhood does not recommend it for production |
| `https://robinhood.drpc.org` | none | yes | dRPC's free public RPC. Times out on very large calls and limits `eth_getLogs` ranges |
| Alchemy, QuickNode, Chainstack and others | required | | listed in [Robinhood's network docs](https://docs.robinhood.com/chain/connecting) |
| Blockscout explorer, `https://robinhoodchain.blockscout.com` | | | not usable from code: scripts get a Cloudflare challenge page, and Blockscout's multichain API (`api.blockscout.com`) needs a key |

A game needs nothing but `eth_call`: read-only, free, no wallet. The ABIs are in `contracts/abi/`, so any Ethereum
library (ethers, viem, web3.py, alloy, Nethereum, ...) can read the contracts on chain ID 4663; the examples here
use none.

### The reads

| Contract | Call | Selector | Answer |
|---|---|---|---|
| SEEKER NET | `chargesOf(1, 2222)` | `0xf6a7f666` | every token's charge (18 decimals) and status, in one call |
| SEEKER NET | `chargeOf(id)`, `statusOf(id)` | `0xde9964e6`, `0xad35efd4` | one token's |
| SEEKER NET | `accD()`, `accA()`, `activatedCount()` | `0x91f9412c`, `0xdb62316d`, `0x06f9e52c` | the game's totals: they change with every move and every recorded activation |
| SEEKER NET | `renderer()` | `0x8ada6b0f` | the renderer's address |
| Renderer | `dischargeOf(id)`, `uplinkOf(id)` | `0x8dc8ec05`, `0x64a666f6` | 18 decimals |
| Renderer | `tokenJSON(id)` | `0x8f7bb179` | the metadata JSON as a string: traits, live values and the picture's URL |
| Multicall3, `0xcA11bde05977b3631167028862bE2a173976CA11` | `aggregate3(calls)` | `0x82ad56cb` | many reads in one request |

The data of a call is its selector followed by each argument as a 32-byte big-endian number. Token 1895's charge:

```sh
curl https://rpc.mainnet.chain.robinhood.com -H 'content-type: application/json' -d '{"jsonrpc":"2.0","id":1,"method":"eth_call","params":[{"to":"0x5aC790269A6c71a51Ba68BF6a3a2647F86788792","data":"0xde9964e60000000000000000000000000000000000000000000000000000000000000767"},"latest"]}'
```

```json
{"jsonrpc":"2.0","id":1,"result":"0x00000000000000000000000000000000000000000000007436e6388dfdf460f5"}
```

`0x7436e6388dfdf460f5` divided by 10^18 is 2,143.78: its charge at that moment.

Every token at once, in JavaScript with no library:

```js
const RPC = 'https://rpc.mainnet.chain.robinhood.com';
const SEEKER_NET = '0x5aC790269A6c71a51Ba68BF6a3a2647F86788792';
const word = n => n.toString(16).padStart(64, '0');

async function ethCall(to, data) {
  const r = await fetch(RPC, {
    method: 'POST',
    headers: {'content-type': 'application/json'},
    body: JSON.stringify({jsonrpc: '2.0', id: 1, method: 'eth_call', params: [{to, data}, 'latest']}),
  });
  const {result, error} = await r.json();
  if (error) throw new Error(error.message);
  return result.slice(2);
}

// chargesOf(1, 2222): two arrays, charges (18 decimals) and statuses
async function allCharges() {
  const hex = await ethCall(SEEKER_NET, '0xf6a7f666' + word(1) + word(2222));
  const at = i => BigInt('0x' + hex.slice(i * 64, i * 64 + 64));
  const c = Number(at(0)) / 32, s = Number(at(1)) / 32, n = Number(at(c));
  return Array.from({length: n}, (_, i) => ({
    token: i + 1,
    charge: Number(at(c + 1 + i)) / 1e18,
    status: Number(at(s + 1 + i)),   // 0 dormant, 1 activated (not recorded), 2 activated, 3 none
  }));
}
```

**Discharge and Uplink of every token.** Send `dischargeOf(id)` or `uplinkOf(id)` for all 2,222 tokens through
Multicall3's `aggregate3`, in batches. Each `uplinkOf` costs about 14,000 gas, so 1,111 to a batch fits the
official RPC; dRPC's free plan needs smaller batches, and 500 worked. `multicall` in `live.py` shows the
encoding.

### From the answers to the look

- Status 0 (Dormant): the stage is `min(floor(charge × 6 / 9,000) + 1, 6)`, and the picture is the token's
  `arweave_uncharged` with `<stage>` replaced by it. Or draw it: `python3 seeker.py <id> --charge <charge>`.
- Status 1 or 2 (Activated): the animated GIF, `arweave_activated`, or `python3 seeker.py <id> --activated`.
- Status 3: no such token (burned).
- The traits show charge, Discharge and Uplink rounded down to whole numbers. Activated seekers have no Discharge
  or Uplink (both read 0).

For one token, `tokenJSON(id)` gives all of it exactly as marketplaces see it, picture URL included. The owner can
still replace the renderer, so a game that must match marketplaces exactly should prefer `tokenJSON` and look up
`renderer()` instead of keeping the address.

### A client loop

A game showing a few seekers (the player's, say) reads `tokenJSON` or `chargeOf` and `statusOf` for those tokens,
batched through `aggregate3`, every minute or so: a few kilobytes each time.

A game showing the whole collection:

1. At start, read `chargesOf(1, 2222)` (about 285 KB of JSON) and, if it shows them, the Discharge and Uplink
   batches (about 1.4 MB more). Also read the game's totals: `accD`, `accA`, `activatedCount` and `renderer`, in
   one `aggregate3` (under 2 KB).
2. Every 30 to 60 seconds, read the totals again. While they are unchanged nobody has moved, recorded an
   activation or replaced the renderer, so every charge has only grown by 50 a day: add
   `50 × seconds / 86,400` to each charge from the last read. A dormant seeker that reaches 9,000 this way is
   activated; Discharge and Uplink stay as they were.
3. When the totals change, read everything again, at most once every five minutes or so. Read everything once
   an hour regardless.

Seekers moved about 70 times a day in mid-October 2026. Checking once a minute, a client following the collection
this way makes about 1,440 small requests a day, plus a full read at most every five minutes while seekers move.

Events can replace the totals check. `eth_getLogs` for SEEKER NET from the last block seen returns these logs,
which name the tokens to read again:

| Event | Topic |
|---|---|
| `Transfer` (every move) | `0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef` |
| `ChargeReleased` (the charge a move gave away) | `0xa650bfd24135ef7b22c9b29b082819d1d3cae98bb0ae3ce4553757efe96738ac` |
| `Activated` (an activation recorded) | `0x3ec796be1be7d03bff3a62b9fa594a60e947c1809bced06d929f145308ae57ce` |
| `RendererUpdated` | `0x482cbbbcf912da3be80deb8503ae1e94c0b7d5d1d0ec0af3d9d6403e06e609ee` |

Blocks come about every 0.1 seconds. The official RPC answered ranges of 1,000,000 blocks (about 28 hours); dRPC's
free plan limits ranges.

**Rate limits.** Neither public RPC publishes numbers. In testing, bursts of 60 requests were all answered. Keep
each client under about one request per second, double the wait after an HTTP 429 or 5xx answer, and switch to the
other RPC when one fails.

### `live.py`

`live.py` does all of the above with the Python standard library (no `requirements.txt` needed), trying the
official RPC first, then dRPC, and splitting any batch an RPC refuses:

```
python3 live.py               # every token's status, charge, stage, Discharge, Uplink and picture, as JSON
python3 live.py 1895          # one token's metadata from the renderer (tokenJSON)
python3 live.py --watch 60    # the client loop: print the tokens whose status, stage, Discharge or Uplink change
```

## Exactness (optional reading)

Nothing in this section is needed to use the folder; it is here for anyone who wants proof.

The drawings are not approximations: they are made by the same code that made the collection, and come out
identical to the collection's art pixel for pixel, every frame of every GIF included. Before the finished files
were left out, all 15,554 of them were re-drawn from this folder and compared file by file: every one matched.
If you ever want to check the whole collection yourself against the checksums (optional, a few minutes on a
laptop, and not needed before using anything):

```
python3 verify.py              # all 2,222 seekers: 13,332 pictures and 2,222 GIFs
python3 verify.py --sample 50  # a quicker check of 50 seekers
```

The only change from the original code is where it finds its files (and that eyes are read from
`layers/eyes/` instead of being drawn in code); see `engine/README.md`.
