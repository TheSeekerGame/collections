# Guardians Art Kit

A compact, offline-capable copy of the final v9 collection artwork and its exact padding-based selection rules. No wallet, private keys, transaction files, or API keys are included.

## Contents

- `assets/backgrounds/`: 15 final backgrounds (including all 12 background2 variants).
- `assets/orbs/`: 15 final orbs.
- `assets/eyes/`: 37 eyes, including the 13 reused original inscriptions.
- `assets/bodies/`: four lossless, gzip-compressed SVG bundles containing shared shapes, palettes, and all 1,843 selectable body states. These preserve the inscribed SVG contents without storing every combination as a separate image.
- `data/assets.json`: every art inscription ID mapped to a local asset file (71 resources).
- `data/selection.json.gz`: the exact final v9 selection JSON, losslessly compressed. Includes weights, category assignments, and fractional selectors.
- `data/body-traits.json.gz`: each body inscription fragment mapped to its source trait names and elements.
- `data/collection.json`: all 333 collectible IDs, collection numbers, immutable four-letter codes, and original HTML hashes.
- `collection.csv`: readable list of all 333 IDs with their background/orb/body/eye categories.
- `data/categories.json.gz`: each category’s available inscription references; combine with `data/assets.json` to locate its local art files. Body references include the required SVG fragment.
- `guardians.py`: selection, rendering, ID import, and asset inspection CLI.
- `live.py`: reads every Guardian's current padding from public ord servers and reports its look (see [Live data for games](#live-data-for-games)).
- `verification.json`: validation results for this package.

This is a snapshot of the final v9 art/configuration, not a service that follows future configuration updates. An inscription's selected assets depend on padding; there is no single permanent set of four selected files per ID. Its code determines available categories, and `inspect` reports the exact four assets at a given padding. [Live data for games](#live-data-for-games) shows how a client reads the current padding and checks that the on-chain rules are still these.

## Collection inscription IDs

All Guardians use this inscription-ID pattern:

```text
0000038e69f964da83318a45cd892abffbc63f73e0d08436d2ade37f5d8b3000iN
```

`N` is the inscription index, from **0 through 332 inclusive** (zero-based inscription indices). For example, the first inscription is:

```text
0000038e69f964da83318a45cd892abffbc63f73e0d08436d2ade37f5d8b3000i0
```

The supplied i1–i333 range was checked: i333 returns 404, while i0 is a valid Guardian with code AAAA. Therefore this kit includes i0–i332. The `number`/`display_number` fields are convenience ordinals 1–333 (index + 1), not independently verified marketplace names. The raw `inscription_index` is authoritative. Each code was extracted from its actual inscription HTML and checked against the original collection renderer. All 333 codes are unique. The inventory is already populated, so no API key or network access is needed to render these Guardians.

```sh
python guardians.py render --id 0000038e69f964da83318a45cd892abffbc63f73e0d08436d2ade37f5d8b3000i0 --padding 1000 --scale 20 --output guardian-1.png
```

## Setup

Python 3.10 or newer and Pillow are required. No Node, browser, SVG engine, or external font is needed.

```sh
cd guardians
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The environment and generated PNGs are not bundled, to keep the distributed folder small.

## Render by inscription ID and padding

```sh
python guardians.py render --id YOUR_INSCRIPTION_ID --padding 1000 --output guardian.png
```

After importing IDs, rendering is fully offline. For an ID not yet imported, use `--fetch-code` once:

```sh
python guardians.py render --id YOUR_INSCRIPTION_ID --padding 1000 --fetch-code --output guardian.png
```

This performs a read-only request to `https://ordinals.com/content/ID`, checks for the original collection renderer, extracts the code without executing inscription HTML, and caches it. It does not prove collection membership: a copied inscription can reference the same renderer. Supply the authoritative collection inventory for that purpose. Internet is otherwise unnecessary. The separately inscribed test Guardian uses another renderer and is intentionally not accepted as a collection member.

Padding means the **total value in sats of the output holding the Guardian**, exactly as used by the on-chain renderer. It is not the inscription's sat offset, extra sats beyond a minimum, or the fee. Pass the current value yourself, or read it with `live.py` (see [Live data for games](#live-data-for-games)). Neither tool moves inscriptions.

## Resolution and transparency

The actual source artwork is **54×54**, not 24×24. Default output is native 54×54. A 20× upscale gives 1080×1080, matching the on-chain renderer. All scaling uses nearest-neighbor filtering.

```sh
python guardians.py render --code FAFC --padding 1000 --scale 20 --output guardian-1080.png
python guardians.py render --code FAFC --padding 1000 --scale 8 --transparent --output guardian-transparent.png
python guardians.py render --code FAFC --padding 1000 --size 24 --output guardian-24.png
```

`--size 24` is a lossy downsample, not native art: small details can disappear. Combine it with `--scale 20` for a 480×480 enlargement of that downsample. `--scale` accepts any positive integer. `--transparent` omits only the background layer, preserving the orb, body, and eyes. Layer order is background → orb → body → eyes.

`--code` can render any valid category code without an inscription manifest; it does not assert that a collectible with that code exists.

## Inspect selected assets

```sh
python guardians.py inspect --id YOUR_INSCRIPTION_ID --padding 1000
python guardians.py inspect --code FAFC --padding 1000
```

The JSON output identifies every selected layer's inscription reference and local file, including the SVG fragment for the body, plus its original trait names and elements. Render commands print the same information. Redirect it to a file to save a per-inscription/padding asset manifest.

## Live data for games

A Guardian's look follows its padding, and its padding is on Bitcoin, so every game that reads the chain shows the same Guardian, single-player games included. No server of ours is involved: clients read public ord servers directly, which is also what the on-chain renderer does.

### What changes

| | Changes | Source |
|---|---|---|
| Code (four letters) | never | `data/collection.json` |
| Art | never: inscriptions are immutable | `assets/` here, or `/content/<inscription id>` on any ord server |
| Padding | when the holder moves the Guardian into an output of a different value | the value of the output holding the Guardian |
| Selection rules | when a new configuration is inscribed on sat `1051634999999999` | the latest inscription on that sat. This kit has `6eb4d607f6161293aac758ba9eced50c5b62f6fc1ff89adf19cf5e7fb0647ccei0` |

A new padding counts once its transaction is in a block. Ord servers index confirmed blocks only, so the look changes for every client at the same block, about ten minutes after the transaction on average.

### Public APIs

As tested on 17 October 2026:

| API | Key | Browser games (CORS) | Use |
|---|---|---|---|
| `https://ordinals.com` | none | yes | primary. The ord project's own server; it serves the recursive endpoints below, while its other JSON API is disabled |
| `https://static.unisat.io` | none | yes | the same recursive endpoints |
| `https://ord-mirror.magiceden.dev` | none | no (allows magiceden.io only) | the same recursive endpoints, for native clients |
| `https://mempool.space/api` | none | yes | a plain Bitcoin explorer: says whether a known output is still unspent, and gives any output's value |
| Ordiscan, `https://api.ordiscan.com/v1` | required. Free tier: 1,000 requests a month, 100 a minute | yes | a last resort; see [Getting the most from an Ordiscan key](#getting-the-most-from-an-ordiscan-key) |
| Hiro Ordinals API | | | shut down (answers 410 Gone) |

The recursive endpoints are the ones inscriptions themselves use, and ord guarantees their backwards compatibility: they will not be removed, and their fields will not be renamed or change type ([ord documentation](https://docs.ordinals.com/inscriptions/recursion.html)). Each answers with JSON.

### Requests

**One Guardian.** `value` is the padding:

```sh
curl https://ordinals.com/r/inscription/0000038e69f964da83318a45cd892abffbc63f73e0d08436d2ade37f5d8b3000i0
```

```json
{
  "id": "0000038e69f964da83318a45cd892abffbc63f73e0d08436d2ade37f5d8b3000i0",
  "output": "742f74e1523a676931d0dee3c60cfbde8e0f0b8055d153c426e018d6eea074b9:0",
  "value": 922
}
```

The answer has more fields (`sat`, `satpoint`, `address`, and others); ignore what you don't need, and expect new fields to appear.

**The whole collection in four requests.** Every Guardian is a child of inscription `1eab87f0048147a37b3be9f0f35227c77a7b258ce37ef1cf4a0e7adb16b20f5ei0`, listed 100 to a page:

```sh
curl https://ordinals.com/r/children/1eab87f0048147a37b3be9f0f35227c77a7b258ce37ef1cf4a0e7adb16b20f5ei0/inscriptions/0
```

Pages 0 to 3 hold all 333 (`"more": false` on the last). Each child has its `id` and `output`, but not the output's value. An output's value can never change, so ask only about outputs you haven't seen before:

```sh
curl https://ordinals.com/r/utxo/742f74e1523a676931d0dee3c60cfbde8e0f0b8055d153c426e018d6eea074b9:0
```

```json
{"inscriptions": ["0000038e69f964da83318a45cd892abffbc63f73e0d08436d2ade37f5d8b3000i0"], "value": 922}
```

Keep only the 333 IDs in `data/collection.json`; the parent could gain other children later.

**The selection rules.** The renderer uses the latest inscription on its configuration sat:

```sh
curl https://ordinals.com/r/sat/1051634999999999/at/-1
```

```json
{"id": "6eb4d607f6161293aac758ba9eced50c5b62f6fc1ff89adf19cf5e7fb0647ccei0"}
```

While the answer is this kit's ID, `data/selection.json.gz` is current. If it ever differs, `/content/<new id>` is the new rules, in the same format; art it names that `data/assets.json` lacks is at `/content/<inscription id>`.

**Anything new?** `/r/blockheight` answers with the latest indexed block height, a bare number. Nothing can change between blocks.

### From padding to look

```js
// selection: the JSON in data/selection.json.gz (or the new rules from /content/<id>)
// code: the Guardian's four letters from data/collection.json
function select(code, padding, selection) {
  let amount = padding;
  return [...code].map((letter, layer) => {   // background, orb, body, eyes
    const group = selection[layer][letter.charCodeAt(0) - 65];
    const r = amount % group.length;
    amount = Math.floor(amount / group.length);
    return group[r];
  });
}
```

This is the on-chain renderer's rule, in IEEE-754 double arithmetic (`%` is `fmod`). Body and eye groups are arrays. Background and orb groups are objects with a fractional `length`, keyed by each possible remainder written the way JavaScript writes numbers (`"0"`, `"0.0078125"`, ...); in other languages, parse the keys as doubles and look up the exact remainder. Each result is an inscription reference: `data/assets.json` maps it to a local file, and a body reference is `<bundle id>#<fragment>`. Paint the four layers in order onto a 54×54 canvas. `python guardians.py inspect --id ID --padding VALUE` gives the same references.

### A client loop

1. At start, load this kit and check the selection rules ID (one request).
2. Ask for `/r/blockheight` every one or two minutes. Bitcoin finds a block every ten minutes on average.
3. On a new block, read the four children pages, then `/r/utxo/<output>` for each output not in your cache. To follow a single Guardian, one `/r/inscription/<id>` replaces all of that.
4. Cache output values and art for good. A look is a pure function of code, padding and rules, so it can be cached by inscription ID and output.
5. Try the servers in the order above and move to the next on any error. If all of them fail, keep showing the cached look. `https://mempool.space/api/tx/<txid>/outspend/<vout>` answers `{"spent": false}` while the cached output still holds the Guardian, which means its padding is unchanged.

Checking every minute, a client makes about 1,440 height requests a day plus five per block, about 2,200 requests a day for the whole collection.

**Rate limits.** None of these ord servers publishes limits or promises uptime. In testing, bursts of 40 requests to each were all answered. Keep each client under about one request per second, double the wait after an HTTP 429 or 5xx answer, and never ask again for a value you have cached.

### Getting the most from an Ordiscan key

Ordiscan's free tier allows 1,000 requests a month (about 33 a day) and 100 a minute, and every request costs one whatever it returns. The key goes in an `Authorization: Bearer <key>` header. Ordiscan gives a Guardian's current output (`owner_output`), and the keyless explorer gives that output's value, which is the padding. To make the requests last:

1. **Spend none while an ord server answers.** For Guardians, the ord servers give everything Ordiscan does, for free.
2. **Find out what changed for free.** Keep each Guardian's last known output. `https://mempool.space/api/tx/<txid>/outspend/<vout>` answers `{"spent": false}` while it still holds the Guardian: nothing to ask. Once it is spent, the answer names the spending transaction (`"txid"`).
3. **One request per Guardian that moved:** `https://api.ordiscan.com/v1/inscription/<id>` answers with `data.owner_output`, as `txid:vout`. Then `https://mempool.space/api/tx/<txid>` gives the padding as `vout[<vout>].value`, at no cost.
4. **One request for many Guardians that moved together.** Group the moved Guardians by their spending transaction. When one transaction moved several, `https://mempool.space/api/tx/<txid>` lists its outputs' addresses (`scriptpubkey_address`). `https://api.ordiscan.com/v1/address/<address>/utxos` lists every output of an address with its `outpoint`, `value` and `inscriptions`, so one request finds every Guardian that went to that address, padding included. Use it when the transaction pays fewer addresses than it moved Guardians: a holder re-padding twenty Guardians in one transaction costs one request instead of twenty.
5. **The player's own Guardians.** When the game knows the player's address, one `/v1/address/<address>/utxos` request gives the output and padding of every Guardian it holds.
6. **Cache every answer and cap each run.** An output's value never changes. A cap (`live.py` stops at 20 requests a run) keeps a long outage of the ord servers from using up the month.
7. **Never ask about the whole collection.** One request per Guardian is a third of the month. The list, collection and traits endpoints give nothing this kit lacks.

| Situation | Ordiscan requests |
|---|---|
| An ord server answers | 0 |
| No ord server answers, and no Guardian moved | 0 (the explorer's `outspend` only) |
| One Guardian moved | 1 |
| Several moved in one transaction that pays *k* addresses | *k*, or one per Guardian if that is fewer |
| The player's Guardians, at a known address | 1 |

### `live.py`

`live.py` runs that loop with the Python standard library and this kit, and caches output values in `live-cache.json`:

```sh
python live.py                  # every Guardian: output, padding, and its four layers, as JSON
python live.py --id 0000038e69f964da83318a45cd892abffbc63f73e0d08436d2ade37f5d8b3000i0
python live.py --watch 60       # each new block, print the Guardians whose look changed
```

Its answer carries the selection rules ID it found (`config`). `config_current` is false, with a warning, once the on-chain rules are no longer this kit's. If no ord server answers, it keeps every Guardian whose cached output is unspent and looks up the ones that moved as described in [Getting the most from an Ordiscan key](#getting-the-most-from-an-ordiscan-key), at most 20 requests a run.

### Open issue: no guaranteed keyless indexer

Good keyless sources exist, but nothing guarantees them. The three ord servers belong to the ord project, UniSat and Magic Eden; none publishes limits, any of them could add a key or close, and only ordinals.com and UniSat accept requests from browser games. The keyed services do not fill that gap well: Hiro's API is gone, and Ordiscan's free tier covers only occasional lookups. One fully keyless fallback remains unimplemented: following each Guardian from its last known location on a plain Bitcoin explorer. A spent output's inscription moves by ordinal theory's first-in, first-out rule, so its new output and value can be computed from the spending transaction (`https://mempool.space/api/tx/<txid>`).

## Import the complete collection list

```sh
python guardians.py import-ids collection-input.json
```

Accepted inputs:

```json
[{"id":"INSCRIPTION_ID","code":"FAFC"}]
```

or an object mapping IDs to codes, or a JSON array of ID strings. IDs without codes are fetched from ordinals.com; supplied codes are validated structurally and trusted, so use an authoritative source. The resulting `data/collection.json` is portable and permits offline ID-based rendering.

## Fidelity and size

The Python renderer decodes the bundles' exact integer pixel rectangles and palette variables. It does not approximate curves or invoke a browser. Every one of the 1,843 body states is checked against its approved RGBA hash. Selector tests compare Python binary64 arithmetic against the actual JavaScript operations across every valid code, including large output values. No asset recoloring is performed.

The package stores shared shapes once per original SVG bundle and compresses repetitive selector/trait data. It avoids duplicate individual body PNGs, preview grids, dependencies, and pre-rendered full Guardians. Original project and inscription files are untouched.
