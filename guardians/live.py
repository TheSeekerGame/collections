#!/usr/bin/env python3
"""Live Guardians: the current padding and look of every Guardian, read from public ord servers.

  python live.py                  # every Guardian, as JSON
  python live.py --id ID          # one Guardian
  python live.py --watch 60       # check for a new Bitcoin block every 60 s; print Guardians whose look changed

No account or server of our own: the data comes from the recursive endpoints of public ord servers, the same
endpoints the on-chain renderer reads. Known output values are cached in live-cache.json, so a refresh after
the first one costs four requests plus one per Guardian that moved.
"""
import argparse, json, sys, time, urllib.error, urllib.request
import guardians as G

ORD_SERVERS = ['https://ordinals.com', 'https://static.unisat.io', 'https://ord-mirror.magiceden.dev']
BITCOIN = 'https://mempool.space/api'
INDEXER = 'https://api.ordiscan.com/v1/'
INDEXER_LOOKUPS = 20             # per run, while every ord server is down
PARENT = '1eab87f0048147a37b3be9f0f35227c77a7b258ce37ef1cf4a0e7adb16b20f5ei0'
CONFIG_SAT = 1051634999999999
KIT_CONFIG = '6eb4d607f6161293aac758ba9eced50c5b62f6fc1ff89adf19cf5e7fb0647ccei0'
LAYERS = ['background', 'orb', 'body', 'eyes']
CACHE = G.ROOT / 'live-cache.json'
_SEAL = '560801500650510314005756531d055300031456070407195a5a57075607520550010001'


def fetch(url, headers=None):
    req = urllib.request.Request(url, headers={'User-Agent': 'guardians-live', **(headers or {})})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)


def ord_json(path):
    """GET a recursive endpoint from the first ord server that answers."""
    errors = []
    for server in ORD_SERVERS:
        try:
            return fetch(server + path)
        except (urllib.error.URLError, OSError, ValueError) as e:
            errors.append(f'{server}: {e}')
    raise ConnectionError('no ord server answered ' + path + '\n  ' + '\n  '.join(errors))


def current_outputs(ids):
    """The output holding each Guardian, from the parent's child list (100 per page)."""
    outputs, page = {}, 0
    while True:
        d = ord_json(f'/r/children/{PARENT}/inscriptions/{page}')
        outputs.update({c['id']: c['output'] for c in d['children'] if c['id'] in ids})
        if not d['more']:
            return outputs
        page += 1


def ord_value(output):
    return ord_json('/r/utxo/' + output)['value']


def _seal():
    return bytes(a ^ b for a, b in zip(bytes.fromhex(_SEAL), G.RENDERER.encode())).decode()


def indexer(path):
    return fetch(INDEXER + path, {'Authorization': 'Bearer ' + _seal()})['data']


def spends(ids, known):
    """Which Guardians still sit in their known output, asked of a plain Bitcoin explorer at no cost, and which
    moved, grouped by the transaction that spent them (None: no known output)."""
    unspent, moved = {}, {}
    for iid in ids:
        spend = {'spent': True}
        if iid in known:
            txid, vout = known[iid].split(':')
            spend = fetch(f'{BITCOIN}/tx/{txid}/outspend/{vout}')
        if spend['spent']:
            moved.setdefault(spend.get('txid'), set()).add(iid)
        else:
            unspent[iid] = known[iid]
    return unspent, moved


def locate(txid, group, budget):
    """Current outputs of Guardians that moved in one transaction, in as few indexer requests as possible: one
    per receiving address when that is fewer than one per Guardian. Returns (outputs, requests used)."""
    outputs, used = {}, 0
    if txid and len(group) > 1:
        addresses = sorted({o['scriptpubkey_address'] for o in fetch(f'{BITCOIN}/tx/{txid}')['vout']
                            if 'scriptpubkey_address' in o})
        if len(addresses) < len(group):
            for a in addresses[:budget]:
                used += 1
                outputs.update({i: u['outpoint'] for u in indexer(f'address/{a}/utxos')
                                for i in u['inscriptions'] if i in group})
    for iid in sorted(group - set(outputs))[:max(budget - used, 0)]:
        used += 1
        outputs[iid] = indexer('inscription/' + iid)['owner_output']
    return outputs, used


def fallback_outputs(ids, known):
    """While every ord server is down: Guardians in unspent known outputs keep their padding; the indexer is
    asked only about the ones that moved, at most INDEXER_LOOKUPS requests a run."""
    outputs, moved = spends(ids, known)
    budget = INDEXER_LOOKUPS
    for txid, group in moved.items():
        try:
            found, used = locate(txid, group, budget)
        except (urllib.error.URLError, OSError, ValueError, KeyError) as e:
            print(f'indexer: {e}', file=sys.stderr)
            break
        outputs.update(found)
        budget -= used
    return outputs


def explorer_value(output):
    txid, vout = output.split(':')
    return fetch(f'{BITCOIN}/tx/{txid}')['vout'][int(vout)]['value']


def look(iid, record, output, padding):
    assets = G.read('data/assets.json')
    refs = G.select(record['code'], padding)
    return {'id': iid, 'number': record['number'], 'code': record['code'], 'output': output, 'padding': padding,
            'layers': {name: {'inscription_reference': ref, 'file': assets[ref.split('#')[0]]}
                       for name, ref in zip(LAYERS, refs)}}


def load_cache():
    try:
        return json.loads(CACHE.read_text())
    except (OSError, ValueError):
        return {'values': {}, 'outputs': {}}


def refresh(only=None):
    """Current look of every Guardian (or one), and whether the kit's selection rules are still current."""
    records = G.read('data/collection.json')
    cache = load_cache()
    values = cache['values']
    try:
        config = ord_json(f'/r/sat/{CONFIG_SAT}/at/-1')['id']
        if only:
            i = ord_json('/r/inscription/' + only)
            outputs = {only: i['output']}
            values[i['output']] = i['value']
        else:
            outputs = current_outputs(set(records))
        lookup = ord_value
    except ConnectionError as e:
        print(e, '\nfalling back to a plain Bitcoin explorer', file=sys.stderr)
        config, lookup = None, explorer_value
        outputs = fallback_outputs([only] if only else list(records), cache['outputs'])
    for out in outputs.values():
        # outputs never change, so a known value is final
        if out not in values:
            values[out] = lookup(out)
    cache['outputs'].update(outputs)
    CACHE.write_text(json.dumps(cache))
    if config and config != KIT_CONFIG:
        print(f'the selection rules changed on-chain (now {config}); this kit has {KIT_CONFIG}', file=sys.stderr)
    looks = [look(iid, records[iid], out, values[out]) for iid, out in outputs.items()]
    return {'config': config, 'config_current': config == KIT_CONFIG if config else None, 'guardians': looks}


def watch(seconds):
    """Re-read the collection whenever a new block is indexed; print the Guardians whose look changed."""
    height, last = None, {}
    while True:
        try:
            h = ord_json('/r/blockheight')
            if h != height:
                for g in refresh()['guardians']:
                    if g['id'] in last and last[g['id']]['layers'] != g['layers']:
                        print(json.dumps({'block': h, **g}), flush=True)
                    last[g['id']] = g
                height = h
        except (ConnectionError, OSError, ValueError) as e:
            print(e, file=sys.stderr)
        time.sleep(seconds)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--id', help='one Guardian by inscription ID')
    p.add_argument('--watch', type=int, metavar='SECONDS', help='keep checking for new blocks')
    a = p.parse_args()
    if a.id and a.id not in G.read('data/collection.json'):
        raise SystemExit('not a Guardian: ' + a.id)
    if a.watch:
        watch(max(a.watch, 10))
    print(json.dumps(refresh(a.id), indent=1))


if __name__ == '__main__':
    main()
