#!/usr/bin/env python3
"""SEEKER NET: draw any token's artwork from the layers in this folder.

    python3 seeker.py 1895                     # what token 1895 shows right now (reads the chain)
    python3 seeker.py 1895 --charge 4200       # token 1895 as an uncharged seeker at 4,200 charge
    python3 seeker.py 1895 --charge 9500       # token 1895 activated: the animated GIF
    python3 seeker.py 1895 --activated --still # the activated seeker as a still picture
    python3 seeker.py 1895 --info              # traits, live charge and the files it uses; draws nothing
    python3 seeker.py 1895 --check             # draw it and compare with the collection's checksum
    python3 seeker.py --artwork 716 --charge 0 # by artwork number instead of token ID

Options:
    --charge N     charge to draw it at (0 to 9,000 = uncharged, above 9,000 = activated)
    --activated    draw the activated version, whatever the charge
    --still        for an activated seeker: a still picture (the GIF's first frame) instead of the GIF
    --scale N      pixels per art pixel; 20 (default) = 1080 x 1080 like the collection, 1 = 54 x 54
    --out FILE     where to write the picture (default: renders/...)
    --rpc URL      the Robinhood Chain RPC to read the live charge from

Without --charge and --activated the token's live charge and status are read
from the SEEKER NET contract (a free, read-only call; no wallet needed).
See README.md.
"""
import argparse
import csv
import hashlib
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'engine'))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import animate_collection as A  # noqa: E402
import final as F  # noqa: E402

RPC = 'https://rpc.mainnet.chain.robinhood.com'
NFT = '0x5aC790269A6c71a51Ba68BF6a3a2647F86788792'
# function selectors (first 4 bytes of keccak256 of the signature)
SELECTOR = {'chargeOf(uint256)': '0xde9964e6', 'statusOf(uint256)': '0xad35efd4',
            'startChargeOf(uint256)': '0x8552a5f4'}
STATUS = {0: 'uncharged', 1: 'activated (over 9,000, not recorded yet)', 2: 'activated', 3: 'does not exist'}
THRESHOLD = 9000
ONE = 10 ** 18
LISTS = os.path.join(HERE, 'lists')
PATH_COLUMNS = ['base_layer', 'eyes_layer', 'object_layer', 'head_layer', 'flank_layer', 'back_layer',
                'background_layer']


def read_csv(name, key):
    with open(os.path.join(LISTS, name), newline='') as fh:
        return {int(r[key]): r for r in csv.DictReader(fh)}


def call(signature, token, rpc):
    """One read-only contract call: an integer answer."""
    data = SELECTOR[signature] + '%064x' % token
    body = json.dumps({'jsonrpc': '2.0', 'id': 1, 'method': 'eth_call',
                       'params': [{'to': NFT, 'data': data}, 'latest']}).encode()
    req = urllib.request.Request(rpc, body, {'content-type': 'application/json', 'User-Agent': 'seeker.py'})
    with urllib.request.urlopen(req, timeout=60) as r:
        answer = json.load(r)
    if 'result' not in answer:
        raise SystemExit(f'the chain refused {signature} for token {token}: {answer.get("error")}')
    return int(answer['result'], 16)


def live(token, rpc):
    """(charge, status) of a token right now, from the contract."""
    status = call('statusOf(uint256)', token, rpc)
    if status == 3:
        raise SystemExit(f'token {token} does not exist')
    return call('chargeOf(uint256)', token, rpc) / ONE, status


def traits(row):
    return {k: (None if row[k] == 'None' else row[k]) for k in F.KEYS}


def background_path(row):
    return os.path.join(HERE, row['background_layer'])


def save_png(im, path, scale):
    """A 54 x 54 picture as an exact PNG, scale x scale pixels per art pixel
    (a palette PNG, like the collection's: nothing is approximated)."""
    rgb = im.convert('RGB')
    data = list(rgb.getdata())
    colours = sorted(set(data))
    pal = Image.new('P', rgb.size)
    flat = [v for c in colours for v in c]
    pal.putpalette(flat + [0] * (768 - len(flat)))
    index = {c: i for i, c in enumerate(colours)}
    pal.putdata([index[c] for c in data])
    pal.resize((54 * scale, 54 * scale), Image.NEAREST).save(path, optimize=True)


def draw_uncharged(row, charge):
    """The uncharged picture at a charge (54 x 54)."""
    return F.compose_dormant(traits(row), F.stage_of(charge))


def draw_activated_frames(row):
    """The activated animation: one frame per 50 ms, as the engine's frames."""
    frames, _ = A.Seeker(traits(row), int(row['artwork']), background_path(row)).render()
    return frames


def draw_activated_still(row):
    """The activated seeker at rest over its background (the GIF's first frame)."""
    return Image.fromarray(A.still(traits(row), background_path(row)).astype(np.uint8))


def pixel_hash(frames):
    """sha256 of a picture's pixels: its 54 x 54 RGB frames, one per 50 ms, one
    after the other (a still: one frame). The lists hold this checksum for every
    finished file of the collection."""
    h = hashlib.sha256()
    for f in frames:
        h.update(np.ascontiguousarray(f, dtype=np.uint8).tobytes())
    return h.hexdigest()


def show_info(token, row, charge, status, source):
    print(f'SEEKER NET #{token}' if token else f'artwork {row["artwork"]}')
    print(f'  artwork {row["artwork"]} (file number {row["file_number"]})')
    print('  ' + ' · '.join(f'{k}: {row[k]}' for k in F.KEYS + ['Background', 'Loadout']))
    print(f'  starting charge {row["starting_charge"]} · Charge Rank {row["charge_rank"]} (0 = rarest)')
    if charge is not None:
        state = STATUS[status] if status is not None else ('activated' if charge > THRESHOLD else 'uncharged')
        stage = '' if charge > THRESHOLD or (status or 0) != 0 else f', picture stage {F.stage_of(charge)} of 6'
        print(f'  charge {charge:,.2f} ({source}): {state}{stage}')
    print('  layers: ' + ', '.join(row[c] for c in PATH_COLUMNS if row[c]))
    print(f'  on Arweave: {row["arweave_activated"]}')
    print(f'              {row["arweave_uncharged"]}')


def main():
    ap = argparse.ArgumentParser(description='Draw a seeker from its layers.')
    ap.add_argument('token', type=int, nargs='?', help='token ID (1 to 2222)')
    ap.add_argument('--artwork', type=int, help='artwork number (0 to 2221) instead of a token ID')
    ap.add_argument('--charge', type=float, help='charge to draw it at (default: the live charge)')
    ap.add_argument('--activated', action='store_true', help='draw the activated version')
    ap.add_argument('--still', action='store_true', help='activated: a still PNG instead of the GIF')
    ap.add_argument('--scale', type=int, default=20, help='pixels per art pixel (20 = 1080 px, 1 = 54 px)')
    ap.add_argument('--out', help='output file')
    ap.add_argument('--rpc', default=RPC, help='Robinhood Chain RPC')
    ap.add_argument('--info', action='store_true', help='print what the token is and uses; draw nothing')
    ap.add_argument('--check', action='store_true', help="also compare with the collection's checksum")
    a = ap.parse_args()
    if (a.token is None) == (a.artwork is None):
        ap.error('give a token ID or --artwork N (one of them)')
    if a.scale < 1:
        ap.error('--scale must be 1 or more')

    if a.token is not None:
        row = read_csv('tokens.csv', 'token').get(a.token)
        if row is None:
            ap.error('token IDs run from 1 to 2222')
    else:
        row = read_csv('artworks.csv', 'artwork').get(a.artwork)
        if row is None:
            ap.error('artwork numbers run from 0 to 2221')
        if a.charge is None and not a.activated:
            ap.error('an artwork has no live charge: give --charge N or --activated')

    status, source = None, 'given'
    charge = a.charge
    if charge is None and not a.activated:
        charge, status = live(a.token, a.rpc)
        source = 'live, read from the chain'
    activated = a.activated or (status is not None and status != 0) or (charge is not None and charge > THRESHOLD)

    show_info(a.token, row, charge, status, source)
    if a.info:
        return

    name = f'token-{a.token}' if a.token is not None else f'artwork-{a.artwork}'
    os.makedirs(os.path.join(HERE, 'renders'), exist_ok=True)
    if activated and not a.still:
        out = a.out or os.path.join(HERE, 'renders', f'{name}-activated.gif')
        frames = draw_activated_frames(row)
        A.save_gif(frames, out, a.scale)
        mine, column = [A.rgb_frame(f) for f in frames], 'activated_pixels_sha256'
    else:
        if activated:
            im = draw_activated_still(row)
            out = a.out or os.path.join(HERE, 'renders', f'{name}-activated-still.png')
            column = 'activated_still_pixels_sha256'
        else:
            im = draw_uncharged(row, charge)
            stage = F.stage_of(charge)
            out = a.out or os.path.join(HERE, 'renders', f'{name}-uncharged-stage{stage}.png')
            column = f'uncharged_stage_{stage}_pixels_sha256'
        save_png(im, out, a.scale)
        mine = [np.array(im.convert('RGB'))]
    print(f'  wrote {os.path.relpath(out)}')

    if a.check:
        same = pixel_hash(mine) == row[column]
        what = {'activated_pixels_sha256': 'the activated GIF',
                'activated_still_pixels_sha256': "the activated GIF's first frame"}.get(column, 'the uncharged picture')
        print(f'  check: identical to {what} in the collection, pixel for pixel ({len(mine)} frame'
              f'{"s" if len(mine) > 1 else ""})' if same else f'  check: DIFFERENT from {what} in the collection')
        if not same:
            sys.exit(1)

if __name__ == '__main__':
    main()
