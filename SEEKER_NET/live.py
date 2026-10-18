#!/usr/bin/env python3
"""Live SEEKER NET: every token's status, charge, picture stage, Discharge and Uplink, read from the chain.

  python3 live.py                # every token, as JSON (six contract reads on the official RPC)
  python3 live.py 1895           # one token: the renderer's own metadata (one call)
  python3 live.py --watch 60     # check the game every 60 s; print tokens whose status, stage,
                                 # Discharge or Uplink changed

Only the Python standard library and a public Robinhood Chain RPC: no wallet, key or server of our own.
"""
import argparse, csv, json, os, sys, time, urllib.error, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RPCS = ['https://rpc.mainnet.chain.robinhood.com', 'https://robinhood.drpc.org']
NFT = '0x5aC790269A6c71a51Ba68BF6a3a2647F86788792'
MULTICALL3 = '0xcA11bde05977b3631167028862bE2a173976CA11'
# function selectors (first 4 bytes of keccak256 of the signature)
CHARGES_OF = '0xf6a7f666'        # chargesOf(uint256,uint256) on SEEKER NET
RENDERER = '0x8ada6b0f'          # renderer() on SEEKER NET
ACC_D, ACC_A = '0x91f9412c', '0xdb62316d'    # accD(), accA() on SEEKER NET: change on every move
ACTIVATED_COUNT = '0x06f9e52c'   # activatedCount() on SEEKER NET
DISCHARGE_OF = '0x8dc8ec05'      # dischargeOf(uint256) on the renderer
UPLINK_OF = '0x64a666f6'         # uplinkOf(uint256) on the renderer
TOKEN_JSON = '0x8f7bb179'        # tokenJSON(uint256) on the renderer
AGGREGATE3 = '0x82ad56cb'        # aggregate3((address,bool,bytes)[]) on Multicall3
BLOCK_TIME = '0x0f28c97d'        # getCurrentBlockTimestamp() on Multicall3
SUPPLY, THRESHOLD, STAGES, ONE, RATE_PER_DAY = 2222, 9000, 6, 10 ** 18, 50
STATUS = ['Dormant', 'Activated (not recorded yet)', 'Activated', 'No such token']
CHUNK, MIN_CHUNK = 1111, 100     # renderer reads per multicall: two batches on the official RPC


def rpc(method, params):
    """One JSON-RPC request, to the first RPC that answers."""
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode()
    errors = []
    for url in RPCS:
        req = urllib.request.Request(url, body, {'content-type': 'application/json', 'User-Agent': 'seeker-live'})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                answer = json.load(r)
            if 'result' in answer:
                return answer['result']
            errors.append(f'{url}: {answer.get("error")}')
        except (urllib.error.URLError, OSError, ValueError) as e:
            errors.append(f'{url}: {e}')
    raise ConnectionError(f'no RPC answered {method}\n  ' + '\n  '.join(errors))


def word(n):
    return '%064x' % n


def call(to, data):
    return bytes.fromhex(rpc('eth_call', [{'to': to, 'data': data}, 'latest'])[2:])


def uint(b, at=0):
    return int.from_bytes(b[at:at + 32], 'big')


def multicall(calls):
    """[(target, calldata)] -> [answer bytes] through Multicall3.aggregate3, in one eth_call."""
    tuples = []
    for target, data in calls:
        b = bytes.fromhex(data[2:])
        tuples.append(word(int(target, 16)) + word(0) + word(96) + word(len(b)) + b.hex().ljust(-(-len(b) // 32) * 64, '0'))
    heads, at = [], 32 * len(tuples)
    for t in tuples:
        heads.append(word(at))
        at += len(t) // 2
    out = call(MULTICALL3, AGGREGATE3 + word(32) + word(len(tuples)) + ''.join(heads) + ''.join(tuples))
    base = uint(out)
    results = []
    for k in range(uint(out, base)):
        t = base + 32 + uint(out, base + 32 + 32 * k)
        data = t + uint(out, t + 32)
        results.append(out[data + 32:data + 32 + uint(out, data)])
    return results


def pulse():
    """What changes when anything happens in the game: the share accumulators (every move), the number of
    recorded activations, and the renderer address. Plus the block time the answer is for."""
    acc_d, acc_a, count, renderer, now = multicall([(NFT, ACC_D), (NFT, ACC_A), (NFT, ACTIVATED_COUNT),
                                                    (NFT, RENDERER), (MULTICALL3, BLOCK_TIME)])
    return {'accD': uint(acc_d), 'accA': uint(acc_a), 'activated': uint(count),
            'renderer': '0x' + renderer[-20:].hex(), 'time': uint(now)}


def charges():
    """(charge, status) of every token, in one call."""
    b = call(NFT, CHARGES_OF + word(1) + word(SUPPLY))
    c, s = uint(b, 0), uint(b, 32)
    n = uint(b, c)
    return [(uint(b, c + 32 + 32 * i), uint(b, s + 32 + 32 * i)) for i in range(n)]


def per_token(renderer, selector, ids=range(1, SUPPLY + 1)):
    """One renderer read for every token. A batch an RPC refuses (gas or time limit) is split in half."""
    if len(ids) > CHUNK:
        return per_token(renderer, selector, ids[:CHUNK]) + per_token(renderer, selector, ids[CHUNK:])
    try:
        return [uint(r) for r in multicall([(renderer, selector + word(i)) for i in ids])]
    except ConnectionError:
        if len(ids) <= MIN_CHUNK:
            raise
        half = len(ids) // 2
        return per_token(renderer, selector, ids[:half]) + per_token(renderer, selector, ids[half:])


def stage(charge, status):
    """The renderer's picture rule: 1-6 while dormant, then the activated GIF."""
    if status:
        return 'activated'
    return min(charge * STAGES // (THRESHOLD * ONE) + 1, STAGES)


def picture(row, st):
    """The token's finished art on Arweave for a stage."""
    return row['arweave_activated'] if st == 'activated' else row['arweave_uncharged'].replace('<stage>', str(st))


def tokens():
    with open(os.path.join(HERE, 'lists', 'tokens.csv'), newline='') as fh:
        return {int(r['token']): r for r in csv.DictReader(fh)}


def snapshot():
    """Every token's live state."""
    p = pulse()
    rows = tokens()
    discharge, uplink = per_token(p['renderer'], DISCHARGE_OF), per_token(p['renderer'], UPLINK_OF)
    out = []
    for i, (charge, status) in enumerate(charges()):
        token, row, st = i + 1, rows[i + 1], stage(charge, status)
        out.append({'token': token, 'artwork': int(row['artwork']), 'status': STATUS[status], 'charge': charge / ONE,
                    'stage': st, 'discharge': discharge[i] / ONE, 'uplink': uplink[i] / ONE, 'picture': picture(row, st)})
    return {'pulse': p, 'tokens': out}


def metadata(token):
    """The renderer's metadata for one token, exactly as marketplaces read it."""
    renderer = '0x' + call(NFT, RENDERER)[-20:].hex()
    b = call(renderer, TOKEN_JSON + word(token))
    at = uint(b)
    return json.loads(b[at + 32:at + 32 + uint(b, at)].decode())


def extrapolate(t, seconds, row):
    """Charge grows 50 a day between moves; the next read picks up shares from other seekers' moves."""
    if t['status'] == 'No such token':
        return t
    charge = t['charge'] + RATE_PER_DAY * seconds / 86400
    if t['status'] == 'Dormant' and charge >= THRESHOLD:
        return {**t, 'charge': float(THRESHOLD), 'status': STATUS[1], 'stage': 'activated',
                'picture': picture(row, 'activated')}
    if t['status'] == 'Dormant':
        st = stage(int(charge * ONE), 0)
        return {**t, 'charge': charge, 'stage': st, 'picture': picture(row, st)}
    return {**t, 'charge': THRESHOLD if t['status'] == STATUS[1] else charge}


def watch(seconds, min_gap=300, max_gap=3600):
    """Read everything once; afterwards only the pulse. Read everything again once the pulse has changed
    (at most every min_gap seconds), and every max_gap seconds regardless."""
    snap, read_at, shown, rows = None, 0, {}, tokens()
    while True:
        try:
            p = pulse()
            age = p['time'] - read_at
            moved = snap and any(p[k] != snap['pulse'][k] for k in ('accD', 'accA', 'activated', 'renderer'))
            if not snap or (moved and age >= min_gap) or age >= max_gap:
                snap, read_at = snapshot(), p['time']
            for t in snap['tokens']:
                now = extrapolate(t, p['time'] - read_at, rows[t['token']])
                view = (now['status'], now['stage'], int(now['discharge']), int(now['uplink']))
                if t['token'] in shown and shown[t['token']] != view:
                    print(json.dumps({'time': p['time'], **now}), flush=True)
                shown[t['token']] = view
        except (ConnectionError, OSError, ValueError) as e:
            print(e, file=sys.stderr)
        time.sleep(seconds)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('token', nargs='?', type=int, help='one token ID, 1 to 2,222')
    ap.add_argument('--watch', type=int, metavar='SECONDS', help='keep checking the game')
    a = ap.parse_args()
    if a.watch:
        watch(max(a.watch, 5))
    if a.token:
        if not 1 <= a.token <= SUPPLY:
            raise SystemExit('token IDs run from 1 to 2,222')
        print(json.dumps(metadata(a.token), indent=1))
    else:
        print(json.dumps(snapshot(), indent=1))


if __name__ == '__main__':
    main()
