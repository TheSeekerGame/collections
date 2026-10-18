"""Shared pieces of the animation pipeline.

    animate_assets.py      export/ + eyes.py  ->  animated/   (frame strips + json)
    animate_collection.py  animated/ + seekers.csv  ->  output/collection/activated/

Timing. Every seeker runs the same clock: 20 frames a second and one
24-frame hover bob that everything shares. A GIF is three bobs long (72
frames, 3.6 s), or four (96 frames, 4.8 s) for a seeker with two acts:

    u = frame % 24      body top   body bottom
    0-1                 0          0            at rest (frame 0 is the still)
    2-3                 -1         0            top leads the rise: 1 px stretch
    4-13                -1         -1           up
    14-15               -1         0            bottom leads the fall: 1 px stretch
    16-23               0          0            at rest

Parts follow the body's top with their own delay (`lag`, in frames); a part
may also be split at a row so its upper rows use a different delay (antenna
tips dragging behind, a propeller leading). The floating object bobs on the
same beat, OBJECT_LAG frames behind.

An animated asset is a strip of cells (CELL x CELL pixels, the 54x54 asset
canvas with PAD pixels of margin all round so motion can leave the canvas the
artist drew on) and a json file next to it. See animated/README.md.
"""
import json
import math
import os

from PIL import Image

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
ANIMATED = os.path.join(ROOT, 'layers', 'animated')

SIZE = 54
LOOPS = (72, 96)              # frames in a GIF: 3 bobs, or 4 for a seeker with two acts
FRAME_MS = 50
BOB = 24                      # frames per hover bob
TWEEN = 2                     # frames of 1 px stretch on each bob move
OBJECT_LAG = 4                # the floating object bobs this many frames behind
PAD = 16                      # margin round the asset canvas in a strip cell
CELL = SIZE + 2 * PAD
STRIP_COLS = 12               # cells per row of a strip

SLOT_DIRS = {'Base': 'base', 'Eyes': 'eyes', 'Floating Object': 'object',
             'Head': 'head', 'Flank': 'flank', 'Back': 'back'}


def bob(f):
    """(top, bottom) offset of a bobbing body at frame f."""
    u = f % BOB
    half = BOB // 2
    if u < 2 or u >= 2 + half + TWEEN:
        return 0, 0
    if u < 2 + TWEEN or u >= 2 + half:
        return -1, 0
    return -1, -1


def slug(name):
    return ''.join(c.lower() if c.isalnum() else '_' for c in name).strip('_')


def rgba(c):
    if isinstance(c, str):
        return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) + (255,)
    return tuple(c[:3]) + (255,)


def hexof(c):
    return c if isinstance(c, str) else '#%02x%02x%02x' % tuple(c[:3])


def asset_path(slot, name, ext):
    return os.path.join(ANIMATED, SLOT_DIRS[slot], slug(name) + ext)


def save_asset(slot, name, frames, meta):
    """Write frames (each {(x, y): colour} in asset coordinates) as a strip,
    and meta as json."""
    os.makedirs(os.path.join(ANIMATED, SLOT_DIRS[slot]), exist_ok=True)
    cols = min(len(frames), STRIP_COLS)
    rows = math.ceil(len(frames) / cols)
    im = Image.new('RGBA', (cols * CELL, rows * CELL), (0, 0, 0, 0))
    for i, px in enumerate(frames):
        ox, oy = (i % cols) * CELL + PAD, (i // cols) * CELL + PAD
        for (x, y), c in px.items():
            if not (-PAD <= x < SIZE + PAD and -PAD <= y < SIZE + PAD):
                raise ValueError(f'{name}: frame {i} pixel {(x, y)} is outside the strip cell')
            im.putpixel((ox + x, oy + y), rgba(c))
    im.save(asset_path(slot, name, '.png'))
    meta = dict({'trait': name, 'slot': slot, 'cell': CELL, 'pad': PAD, 'cols': cols,
                 'frames': len(frames)}, **meta)
    with open(asset_path(slot, name, '.json'), 'w') as fh:
        fh.write(dumps(meta))


def load_asset(slot, name):
    """(meta, frames) with frames as [{(x, y): '#rrggbb'}] in asset coordinates."""
    with open(asset_path(slot, name, '.json')) as fh:
        meta = json.load(fh)
    im = Image.open(asset_path(slot, name, '.png')).convert('RGBA')
    cell, pad, cols = meta['cell'], meta['pad'], meta['cols']
    data = im.load()
    frames = []
    for i in range(meta['frames']):
        ox, oy = (i % cols) * cell, (i // cols) * cell
        px = {}
        for y in range(cell):
            for x in range(cell):
                p = data[ox + x, oy + y]
                if p[3]:
                    px[(x - pad, y - pad)] = '#%02x%02x%02x' % p[:3]
        frames.append(px)
    return meta, frames


def dumps(meta):
    """json with short lists kept on one line."""
    def enc(v, ind):
        pad = '  ' * ind
        if isinstance(v, dict):
            if not v:
                return '{}'
            return '{\n' + ',\n'.join(f'{pad}  {json.dumps(k)}: {enc(x, ind + 1)}'
                                      for k, x in v.items()) + f'\n{pad}}}'
        if isinstance(v, list) and any(isinstance(x, dict) for x in v):
            return '[\n' + ',\n'.join(f'{pad}  {enc(x, ind + 1)}' for x in v) + f'\n{pad}]'
        return json.dumps(v, separators=(',', ':'))
    return enc(meta, 0) + '\n'
