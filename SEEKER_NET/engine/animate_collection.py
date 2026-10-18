"""Combine the animated assets into the collection's activated GIFs.

    python3 generator/animate_collection.py --all                 # 1.gif ... 2222.gif (2222 = artwork 0)
    python3 generator/animate_collection.py --index 0 17 2153     # a few seekers
    python3 generator/animate_collection.py --all --verify        # check only, write nothing

Reads the seekers from output/collection/locked/seekers.csv (never re-rolls
them), each seeker's background from locked/backgrounds.csv (written by
assign_backgrounds.py; --black leaves it out), the animated assets from
animated/ (built by animate_assets.py) and the placement rules from final.py,
and writes one GIF per seeker, named by its artwork index.

How a seeker is put together, per frame:

  body      the hover bob (animkit.bob) plus whatever an add-on's act adds to
            it (a propeller lifting the seeker); split at the monitor's row
            so the top leads and the bottom follows
  eyes      ride the body's top; blink; a scanline rolls down the screen
  hat       rides the lid; its upper rows may drag behind or lead
  back      rides the lid a frame late, hidden wherever the body is
  flank     follows the body a frame or two late
  object    bobs on the same beat, a few frames behind the seeker

Each asset offers one or more variants, most ambitious first. A variant is
used only if, for this seeker, every pixel of every frame stays inside the
54x54 picture and the seeker never touches its floating object; otherwise
the next one is tried.

Timing of a GIF. Acts (the big motions of a hat or a flank add-on) start on
frame 0 and run one after another, never at the same time. A seeker with no
act or one act loops in three bobs (3.6 s); one with two acts in four (4.8 s).
The smaller once-per-loop motions (typing, lamps, glints) start within the
first half second, a little apart from each other.

Frame 0 of every GIF is exactly final.compose(t): a viewer that shows only
the first frame shows the still.
"""
import argparse
import csv
import itertools
import math
import os
import sys
import time
from functools import lru_cache
from multiprocessing import Pool

import numpy as np
from PIL import Image

import animkit as K
import eyes as E
import final as F
from palette import COLORWAYS

LIST = os.path.join(K.ROOT, 'lists', 'artworks.csv')
BACKGROUNDS = os.path.join(K.ROOT, 'lists', 'artworks.csv')
OUT = os.path.join(K.ROOT, 'renders')
SCANLINE = '#0e1c22'              # a dark teal, barely off black
ACT_SLOTS = ('Head', 'Flank')     # slots whose assets may have an act
# once-per-loop motions start in this order, EVENT_GAP frames apart
EVENT_ORDER = ('Back', 'Floating Object', 'Head', 'Flank', 'Base', 'Eyes')
EVENT_GAP = 8

# ------------------------------------------------------------ colours
_ids = {'#000000': 0}
_rgb = [(0, 0, 0)]


def cid(h):
    """A global integer id for a colour (0 = black)."""
    if h not in _ids:
        _ids[h] = len(_rgb)
        _rgb.append(tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)))
    return _ids[h]


# ------------------------------------------------------------ sprites
class Sprite:
    """One frame of an asset as coordinate arrays (asset coordinates)."""
    __slots__ = ('x', 'y', 'c')

    def __init__(self, px):
        pts = sorted(px)
        self.x = np.array([p[0] for p in pts], np.int32)
        self.y = np.array([p[1] for p in pts], np.int32)
        self.c = np.array([cid(px[p]) for p in pts], np.int32)

    def side(self, left):
        s = Sprite({})
        m = self.x < 27 if left else self.x >= 27
        s.x, s.y, s.c = self.x[m], self.y[m], self.c[m]
        return s


@lru_cache(maxsize=None)
def asset(slot, name, colorway=None):
    """(meta, [Sprite]) of an animated asset, recoloured for a colorway."""
    meta, frames = K.load_asset(slot, name)
    if colorway:
        pal = COLORWAYS[colorway]
        swap = F.ROLE_SWAP.get((name, colorway), {})     # final.py's hand-picked exceptions

        def col(c):
            role = F.MASTER.get(c)
            return pal[swap.get(role, role)] if role else c

        frames = [{p: col(c) for p, c in px.items()} for px in frames]
    return meta, [Sprite(px) for px in frames]


# ------------------------------------------------------------ placement
def uniform_shift(addon, base_name, mdy):
    """How final.placed moves a hat or back add-on (one shift for all of it)."""
    src = F.layer(F.SLOTS[F.slot_of(addon)][addon])
    dst = F.placed(addon, base_name, mdy)
    dx = min(x for x, _ in dst) - min(x for x, _ in src)
    dy = min(y for _, y in dst) - min(y for _, y in src)
    assert F.shift(src, dx, dy) == dst, (addon, base_name)
    return dx, dy


def flank_shifts(addon, base_name, mdy):
    """{'L': (dx, dy), 'R': (dx, dy)}: final.placed moves each side on its own."""
    ref, b = F.base(F.REF), F.base(base_name)
    px = F.layer(F.FLANK[addon])
    nx, ny = F.NUDGE.get(addon, (0, 0))
    out, check = {}, {}
    for part, side in zip(F._split(px), 'LR'):
        if not part:
            continue
        g_ref, g_new = F._gap(part, ref, side), F._gap(part, b, side)
        dx = 0 if g_ref is None or g_new is None else g_ref - g_new
        out[side] = ((-dx if side == 'L' else dx) + nx, mdy + ny)
        check.update(F.shift(part, *out[side]))
    assert check == F.placed(addon, base_name, mdy), (addon, base_name)
    return out


def eye_shift(name, base_name):
    """How final.eye_px moves an eye glyph onto a monitor's screen."""
    b = F.base(base_name)
    g = E.EYES[name]()
    pts = [(x, y) for y in range(54) for x in range(54) if g.get(x, y) != '.']
    xs = [x for x, _ in pts]
    ys = [y for _, y in pts]
    dx = F._rnd(b.eye_c[0] - (min(xs) + max(xs)) / 2)
    v = b.eye_c[1] - (min(ys) + max(ys)) / 2
    down = name in F.EYES_LEAN_DOWN or base_name in F.BASES_EYES_LEAN_DOWN
    return dx, (F._rnd(v) if down else math.ceil(v - 0.5))


# ------------------------------------------------------------ tracks
def clip(variant, key, i, default=0):
    """Value of an act's track at act frame i."""
    seq = variant.get('act', {}).get(key)
    if not seq:
        return default
    return default if seq[i] is None else seq[i]


class Part:
    """An asset on a seeker: its sprites, its variant, and when it plays.

    Its loop is either a cycle (its length divides the bob, so it repeats
    for ever: flames, reels, a beacon) or an event (anything longer: it plays
    `reps` times from frame `offset`, then rests on the still)."""

    def __init__(self, slot, name, colorway):
        self.slot = slot
        self.meta, self.sprites = asset(slot, name, colorway)
        self.ride = self.meta.get('ride', {})
        self.variant = self.meta['variants'][0]
        self.start = None                     # frame the act starts at
        self.offset, self.reps = 0, 1

    def period(self):
        return len(self.variant['loop']['seq'])

    def is_event(self):
        return K.BOB % self.period() != 0

    def acting(self, f):
        act = self.variant.get('act')
        if act and self.start is not None and self.start <= f < self.start + len(act['seq']):
            return f - self.start
        return None

    def at(self, f, key, default=0):
        i = self.acting(f)
        if i is not None:
            return clip(self.variant, key, i, default)
        seq = self.variant['loop'].get(key)
        if not seq:
            return default
        n = self.period()
        if not self.is_event():
            return seq[f % n]
        t = f - self.offset
        return seq[t % n] if 0 <= t < self.reps * n else default


def split_paint(sp, split, top, bottom):
    """Coordinates of a sprite whose rows above `split` move by `top` and the
    rest by `bottom` (asset coordinates). When the upper part is the higher
    one, the row just above the split is repeated to bridge the gap, so the
    sprite stretches instead of tearing. Painted in order: lower, bridge, upper."""
    if split is None or top == bottom:
        return sp.x, sp.y + top, sp.c
    up = sp.y < split
    xs, ys, cs = [sp.x[~up]], [sp.y[~up] + bottom], [sp.c[~up]]
    if top < bottom:
        row = sp.y == split - 1
        for k in range(top + 1, bottom + 1):
            xs.append(sp.x[row])
            ys.append(sp.y[row] + k)
            cs.append(sp.c[row])
    xs.append(sp.x[up])
    ys.append(sp.y[up] + top)
    cs.append(sp.c[up])
    return np.concatenate(xs), np.concatenate(ys), np.concatenate(cs)


class OutOfFrame(Exception):
    pass


def put(canvas, x, y, c, mask=None, solid=None):
    if len(x) == 0:
        return
    if x.min() < 0 or y.min() < 0 or x.max() >= K.SIZE or y.max() >= K.SIZE:
        raise OutOfFrame
    if mask is not None:
        keep = ~mask[y, x]
        x, y, c = x[keep], y[keep], c[keep]
    canvas[y, x] = c
    if solid is not None:
        solid[y, x] = True


def outside(solid):
    """The empty pixels that can be reached from the edge of the picture
    (up, down, left, right). That is where a background shows; empty pixels
    shut in by the art - the dark side of a floating object, the gap in a
    mast - stay black, as they are in the still."""
    empty = ~solid
    out = np.zeros_like(empty)
    out[0], out[-1], out[:, 0], out[:, -1] = empty[0], empty[-1], empty[:, 0], empty[:, -1]
    while True:
        grow = out.copy()
        grow[1:] |= out[:-1]
        grow[:-1] |= out[1:]
        grow[:, 1:] |= out[:, :-1]
        grow[:, :-1] |= out[:, 1:]
        grow &= empty
        if (grow == out).all():
            return out
        out = grow


def assigned_backgrounds(path=None):
    """{index: (name, picture path)} from locked/backgrounds.csv, the list
    written by assign_backgrounds.py."""
    out = {}
    with open(path or BACKGROUNDS) as fh:
        for r in csv.DictReader(fh):
            out[int(r['index'])] = (r['Background'], os.path.join(K.ROOT, r['background_layer']))
    return out


def load_background(path):
    im = Image.open(path).convert('RGB')
    if im.size != (K.SIZE, K.SIZE):
        raise ValueError(f'{path}: a background must be {K.SIZE}x{K.SIZE}')
    return np.array(im)


# ------------------------------------------------------------ a seeker
def traits(row):
    return {k: (None if row[k] == 'None' else row[k]) for k in F.KEYS}


def mix(index, salt):
    """A small repeatable pseudo-random number for a seeker."""
    v = (index + 1) * 2654435761 + salt * 40503
    v ^= v >> 13
    v = (v * 1274126177) & 0xffffffff
    return v ^ (v >> 16)


class Seeker:
    def __init__(self, t, index=0, background=None):
        """background: path of a 54x54 picture to put behind the seeker."""
        self.t, self.index = t, index
        self.bg = None
        if background:
            rgb = load_background(background)
            self.bg = np.array([[cid('#%02x%02x%02x' % tuple(p)) for p in row] for row in rgb], np.int32)
        self._outside = {}
        b = self.base = F.base(t['Base'])
        self.mdy, _, self.ody = F.layout(t)
        self.sx, self.odx = F.scene_fit(t) or (0, 0)
        cw = t['Colorway']
        self.parts = {'Base': Part('Base', t['Base'], cw),
                      'Eyes': Part('Eyes', t['Eyes'], None)}
        if t.get('Floating Object'):
            self.parts['Floating Object'] = Part('Floating Object', t['Floating Object'], None)
        for slot in ('Back', 'Flank', 'Head'):
            if t.get(slot):
                self.parts[slot] = Part(slot, t[slot], cw)
        self.shift = {'Base': (self.sx, self.mdy)}
        ex, ey = eye_shift(t['Eyes'], t['Base'])
        self.shift['Eyes'] = (ex + self.sx, ey + self.mdy)
        if t.get('Floating Object'):
            self.shift['Floating Object'] = (self.odx + self.sx, self.ody)
        for slot in ('Head', 'Back'):
            if t.get(slot):
                dx, dy = uniform_shift(t[slot], t['Base'], self.mdy)
                self.shift[slot] = (dx + self.sx, dy)
        if t.get('Flank'):
            self.shift['Flank'] = {s: (dx + self.sx, dy) for s, (dx, dy)
                                   in flank_shifts(t['Flank'], t['Base'], self.mdy).items()}
        self.vol = Sprite({p: '#000000' for p in b.vol})
        scr = sorted(b.screen)
        self.screen = (np.array([p[0] for p in scr], np.int32), np.array([p[1] for p in scr], np.int32))
        self.screen_top = min(p[1] for p in scr)
        self.loop = min(K.LOOPS)
        self.blinks = {}

    # -------------------------------------------------------- schedule
    def schedule(self):
        """Lay the loop out. Acts start on frame 0 and follow each other (in
        an order that differs from seeker to seeker); the loop is three
        bobs, or four when the acts need them. Once-per-loop motions start
        EVENT_GAP frames apart and repeat while there is room."""
        acts = [p for s, p in self.parts.items() if s in ACT_SLOTS and p.variant.get('act')]
        for p in self.parts.values():
            p.start, p.offset, p.reps = None, 0, 1
        if mix(self.index, 3) & 1:
            acts.reverse()
        at = 0
        for p in acts:
            p.start = at
            at += math.ceil(len(p.variant['act']['seq']) / K.BOB) * K.BOB
        fits = [n for n in K.LOOPS if n >= at and (n > at or len(acts) > 1)]
        if not fits:
            return False
        self.loop = fits[0]
        k = 0
        for slot in EVENT_ORDER:
            p = self.parts.get(slot)
            if p and p.is_event():
                if p.period() > self.loop:
                    return False
                p.offset = min(EVENT_GAP * k, self.loop - p.period())
                p.reps = (self.loop - p.offset) // p.period()
                k += 1
        self.blinks = self.blink_frames(at)
        return True

    def blink_frames(self, acts_end):
        """{frame: 'half' | 'shut'}. With no act: a double blink as the loop
        opens and a single one later. With acts: a double blink in the calm
        after them (or, when they fill the loop, single blinks as each one
        starts). The exact frames differ from seeker to seeker."""
        jitter = mix(self.index, 1) % 6
        if acts_end == 0:
            starts = (3, 9, 38 + mix(self.index, 2) % 22)
        elif acts_end < self.loop:
            starts = (acts_end + 2 + jitter, acts_end + 8 + jitter)
        else:
            starts = (1 + jitter, K.LOOPS[-1] // 2 + 1 + jitter)
        out = {}
        for start in starts:
            for n, state in enumerate(('half', 'shut', 'half')):
                out[(start + n) % self.loop] = state
        return out

    # -------------------------------------------------------- motion
    def alt(self, f):
        t = b = 0
        for p in self.parts.values():
            i = p.acting(f)
            if i is not None:
                a = clip(p.variant, 'alt', i, None)
                if a:
                    t, b = t + a[0], b + a[1]
        return t, b

    def body(self, f):
        """(top, bottom) offset of the monitor at frame f."""
        f %= self.loop
        bt, bb = K.bob(f)
        at, ab = self.alt(f)
        return bt + at, bb + ab

    def eye_state(self, f):
        for p in self.parts.values():
            i = p.acting(f)
            if i is not None:
                s = clip(p.variant, 'eyes', i, None)
                if s:
                    return s
        return self.blinks.get(f, 'open')

    # -------------------------------------------------------- painting
    def frame(self, f):
        c = np.zeros((K.SIZE, K.SIZE), np.int32)
        solid = np.zeros((K.SIZE, K.SIZE), bool)          # pixels covered by art
        P = self.parts
        top, bottom = self.body(f)
        base = P['Base']
        split = base.ride.get('split')

        o = P.get('Floating Object')
        obj = None
        if o:
            ot, ob = K.bob(f - o.ride.get('lag', K.OBJECT_LAG))
            x, y, col = split_paint(o.sprites[o.at(f, 'seq')], o.ride.get('split'), ot, ob)
            dx, dy = self.shift['Floating Object']
            x, y = x + dx + o.at(f, 'dx'), y + dy + o.at(f, 'dy')
            put(c, x, y, col, solid=solid)
            obj = np.zeros((K.SIZE, K.SIZE), bool)
            obj[y, x] = True

        vx, vy, _ = split_paint(self.vol, split, top, bottom)
        sx, sy = self.shift['Base']
        hidden = np.zeros((K.SIZE, K.SIZE), bool)
        hidden[np.clip(vy + sy, 0, K.SIZE - 1), np.clip(vx + sx, 0, K.SIZE - 1)] = True

        seeker = np.zeros((K.SIZE, K.SIZE), bool)

        def addon(slot, sprite, shift, lag, mask=None):
            p = P[slot]
            r = p.ride
            low = self.body(f - lag)[0]
            high = self.body(f - r['upper_lag'])[0] if 'split' in r else low
            x, y, col = split_paint(sprite, r.get('split'), high, low)
            x, y = x + shift[0] + p.at(f, 'dx'), y + shift[1] + p.at(f, 'dy')
            put(c, x, y, col, mask, solid)
            seeker[y, x] = True

        if 'Back' in P:
            p = P['Back']
            addon('Back', p.sprites[p.at(f, 'seq')], self.shift['Back'], p.ride.get('lag', 1), hidden)
            seeker[hidden] = False

        x, y, col = split_paint(base.sprites[base.at(f, 'seq')], split, top, bottom)
        put(c, x + sx, y + sy, col, solid=solid)
        seeker[y + sy, x + sx] = True

        if 'Flank' in P:
            p = P['Flank']
            sp = p.sprites[p.at(f, 'seq')]
            lag = p.ride.get('lag', 1)
            for side, shift in self.shift['Flank'].items():
                addon('Flank', sp.side(side == 'L'), shift,
                      lag[side] if isinstance(lag, dict) else lag)
        if 'Head' in P:
            p = P['Head']
            addon('Head', p.sprites[p.at(f, 'seq')], self.shift['Head'], p.ride.get('lag', 0))

        # screen: scanline, then the eyes over it (both clipped to the glass)
        scr = np.zeros((K.SIZE, K.SIZE), bool)
        scr[self.screen[1] + sy + top, self.screen[0] + sx] = True
        row = self.screen_top + f % (self.loop // 2) - 2      # the scanline rolls twice a loop
        line = self.screen[1] == row
        c[self.screen[1][line] + sy + top, self.screen[0][line] + sx] = cid(SCANLINE)
        e = P['Eyes']
        state = self.eye_state(f)
        k = e.meta['states'][state] if state != 'open' else e.at(f, 'seq')
        sp = e.sprites[k]
        ex, ey = self.shift['Eyes']
        x, y = sp.x + ex, sp.y + ey + top
        keep = (x >= 0) & (x < K.SIZE) & (y >= 0) & (y < K.SIZE)
        x, y, col = x[keep], y[keep], sp.c[keep]
        keep = scr[y, x]
        c[y[keep], x[keep]] = col[keep]

        if obj is not None:                    # the seeker must not touch its object
            near = seeker.copy()
            near[1:] |= seeker[:-1]
            near[:-1] |= seeker[1:]
            near[:, 1:] |= near[:, :-1].copy()
            near[:, :-1] |= near[:, 1:].copy()
            if (near & obj).any():
                raise OutOfFrame
        if self.bg is not None:
            key = solid.tobytes()
            if key not in self._outside:
                self._outside[key] = outside(solid)
            out = self._outside[key]
            c[out] = self.bg[out]
        return c

    def render(self):
        """All frames, with the most ambitious variants that fit this seeker.
        Returns (frames, {slot: variant name})."""
        slots = list(self.parts)
        options = [range(len(self.parts[s].meta['variants'])) for s in slots]
        for pick in itertools.product(*options):
            for s, i in zip(slots, pick):
                self.parts[s].variant = self.parts[s].meta['variants'][i]
            if not self.schedule():
                continue
            try:
                frames = [self.frame(f) for f in range(self.loop)]
            except OutOfFrame:
                continue
            picked = {s: self.parts[s].variant['name'] for s in slots}
            picked['Loop'] = f'{self.loop} frames'
            return frames, picked
        raise RuntimeError(f'seeker {self.index}: no variant fits')


# ------------------------------------------------------------ output
def to_images(frames, scale):
    """Palette images (one palette for the whole GIF) and their durations,
    consecutive identical frames merged."""
    used = sorted({int(v) for fr in frames for v in np.unique(fr)})
    if len(used) > 256:
        raise RuntimeError(f'{len(used)} colours')
    lut = np.zeros(max(used) + 1, np.uint8)
    lut[used] = np.arange(len(used), dtype=np.uint8)
    pal = [v for i in used for v in _rgb[i]]
    pal += [0] * (768 - len(pal))
    images, durations, last = [], [], None
    for fr in frames:
        if last is not None and np.array_equal(fr, last):
            durations[-1] += K.FRAME_MS
            continue
        last = fr
        a = lut[fr]
        if scale > 1:
            a = np.repeat(np.repeat(a, scale, axis=0), scale, axis=1)
        im = Image.frombytes('P', (a.shape[1], a.shape[0]), a.tobytes())
        im.putpalette(pal)
        images.append(im)
        durations.append(K.FRAME_MS)
    return images, durations


def save_gif(frames, path, scale):
    """Write the GIF. Pillow's optimiser is on (it stores only what changed
    between frames, which halves the file); read_gif() checks that every
    pixel still comes back exactly."""
    images, durations = to_images(frames, scale)
    images[0].save(path, save_all=True, append_images=images[1:], duration=durations,
                   loop=0, optimize=True, disposal=1)


def read_gif(path, scale):
    """The frames of a GIF as RGB arrays at 54 px, one per 50 ms."""
    out = []
    with Image.open(path) as im:
        for k in range(im.n_frames):
            im.seek(k)
            a = np.array(im.convert('RGB'))[::scale, ::scale]
            out += [a] * max(1, round(im.info.get('duration', K.FRAME_MS) / K.FRAME_MS))
    return out


def rgb_frame(fr):
    return np.array(_rgb, np.uint8)[fr]


def still(t, background=None):
    """The still a GIF's first frame must equal: final.compose(t), over the
    background if there is one."""
    if not background:
        return np.array(F.compose(t).convert('RGB'))
    a = np.array(F.compose(t, background=(0, 0, 0, 0)))
    rgb = a[..., :3].copy()
    rgb[a[..., 3] == 0] = 0
    out = outside(a[..., 3] > 0)
    rgb[out] = load_background(background)[out]
    return rgb


def work(job):
    index, row, out, scales, verify, bg = job
    t = traits(row)
    m = Seeker(t, index, bg and bg[1])
    frames, picked = m.render()
    if bg:
        picked['Background'], bg = bg
    ok = bool((rgb_frame(frames[0]) == still(t, bg)).all())
    sizes = []
    if not verify:
        want = [rgb_frame(fr) for fr in frames]
        for folder, scale in scales:
            path = os.path.join(out, folder, f'{F.file_number(index)}.gif')
            save_gif(frames, path, scale)
            got = read_gif(path, scale)
            ok = ok and len(got) == len(want) and all((a == b).all() for a, b in zip(got, want))
            sizes.append(os.path.getsize(path))
    return index, ok, picked, sizes


def rows():
    with open(LIST) as fh:
        return list(csv.DictReader(fh))


def grid(indices, path, cols, scale=4, bg=None):
    """One GIF of several seekers side by side, to see them move together.
    bg: {index: (name, picture path)} or None for black."""
    listed = rows()
    bg = bg or {}
    cells = [Seeker(traits(listed[i]), i, bg[i][1] if i in bg else None).render()[0]
             for i in indices]
    n = math.ceil(len(cells) / cols)
    frames = []
    for f in range(math.lcm(*{len(c) for c in cells})):     # until every loop is back at its start
        sheet = np.zeros((n * K.SIZE, cols * K.SIZE), np.int32)
        for k, cell in enumerate(cells):
            y, x = (k // cols) * K.SIZE, (k % cols) * K.SIZE
            sheet[y:y + K.SIZE, x:x + K.SIZE] = cell[f % len(cell)]
        frames.append(sheet)
    save_gif(frames, path, scale)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--index', type=int, nargs='*', default=[])
    ap.add_argument('--scale', type=int, default=10, help='whole-number upscale of the main folder')
    ap.add_argument('--native', action='store_true', help='also write 54 px GIFs to activated_54/')
    ap.add_argument('--out', default=OUT)
    ap.add_argument('--folder', default='activated', help='name of the folder the GIFs go in')
    ap.add_argument('--black', action='store_true',
                    help='plain black instead of the backgrounds in locked/backgrounds.csv')
    ap.add_argument('--gallery', action='store_true',
                    help='also write <folder>_gallery.html beside the folder, to look through them')
    ap.add_argument('--verify', action='store_true', help='render and check, write nothing')
    ap.add_argument('--jobs', type=int, default=os.cpu_count())
    ap.add_argument('--grid', metavar='GIF', help='write the --index seekers as one grid GIF instead')
    ap.add_argument('--cols', type=int, default=4)
    a = ap.parse_args()
    bg = {} if a.black else assigned_backgrounds()
    if a.grid:
        grid(a.index, a.grid, a.cols, a.scale, bg)
        print(a.grid, os.path.getsize(a.grid) // 1024, 'KB')
        return 0

    listed = rows()
    wanted = range(len(listed)) if a.all else a.index
    scales = [(a.folder, a.scale)] + ([(a.folder + '_54', 1)] if a.native else [])
    if not a.verify:
        for folder, _ in scales:
            os.makedirs(os.path.join(a.out, folder), exist_ok=True)
    jobs = [(i, listed[i], a.out, scales, a.verify, bg.get(i)) for i in wanted]
    t0 = time.time()
    if a.jobs > 1 and len(jobs) > 8:
        with Pool(a.jobs) as pool:
            results = pool.map(work, jobs, chunksize=8)
    else:
        results = [work(j) for j in jobs]
    bad = [i for i, ok, _, _ in results if not ok]
    tally = {}
    for _, _, picked, _ in results:
        for slot, name in picked.items():
            tally.setdefault(slot, {}).setdefault(name, 0)
            tally[slot][name] += 1
    print(f'{len(results)} seekers in {time.time() - t0:.0f}s')
    print('first frame differs from the still, or a file does not decode exactly:',
          bad if bad else 'none')
    for slot, names in tally.items():
        if len(names) > 1 or 'still' not in names:
            print(f'  {slot}: ' + ', '.join(f'{n} {c}' for n, c in sorted(names.items())))
    if not a.verify:
        for k, (folder, scale) in enumerate(scales):
            sz = sorted(s[k] for _, _, _, s in results)
            print(f'{folder} ({54 * scale}px): {len(sz)} files, smallest {sz[0] // 1024} KB, '
                  f'median {sz[len(sz) // 2] // 1024} KB, largest {sz[-1] // 1024} KB, '
                  f'total {sum(sz) / 1e6:.0f} MB')
    if a.gallery and not a.verify:
        gallery(os.path.join(a.out, a.folder), listed, results)
    return 1 if bad else 0


def gallery(folder, listed, results):
    """A page of the rendered GIFs with their traits, for reviewing by eye."""
    cards = []
    name = os.path.basename(folder.rstrip('/'))
    for index, _, picked, _ in sorted(results):
        r = listed[index]
        parts = [r[k] for k in ('Base', 'Colorway', 'Eyes', 'Floating Object') if r[k] != 'None']
        extra = []
        for k in ('Head', 'Flank', 'Back'):
            if r[k] != 'None':
                v = picked.get(k, '')
                extra.append(r[k] + (f' ({v})' if v not in ('loop', 'still', '') else ''))
        bg = f'<br>{picked["Background"]}' if 'Background' in picked else ''
        cards.append(f'<figure><img src="{name}/{F.file_number(index)}.gif" loading="lazy" width="270" height="270">'
                     f'<figcaption><b>#{index}</b> {r["Loadout"]}<br>{" · ".join(parts)}'
                     f'<br>{" · ".join(extra) or "no add-ons"}{bg}</figcaption></figure>')
    page = ('<!doctype html><meta charset="utf-8"><title>SEEKER NET: activated preview</title>'
            '<style>body{background:#111;color:#bbb;font:12px/1.4 system-ui;margin:16px}'
            'main{display:grid;grid-template-columns:repeat(auto-fill,270px);gap:16px}'
            'figure{margin:0}img{image-rendering:pixelated;display:block;background:#000}'
            'figcaption{padding:6px 2px}b{color:#fff}</style>'
            f'<h3>{len(cards)} activated seekers</h3><main>' + ''.join(cards) + '</main>')
    # beside the folder, not in it: the folder itself is uploaded as it is
    with open(folder.rstrip('/') + '_gallery.html', 'w') as fh:
        fh.write(page)


if __name__ == '__main__':
    sys.exit(main())
