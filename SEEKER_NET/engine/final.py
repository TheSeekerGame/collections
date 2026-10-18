"""The final collection, built from the artist's polished assets in export/.

    python3 generator/final.py --grids 3          # preview grids
    python3 generator/final.py --report           # compatibility report

Every asset was drawn by the artist on the Classic base, in the master
colorway. Positioning rules move each one onto other bases by comparing the
geometry of the target base with the Classic:

  Hat      stands on the lid: its bottom row one above the lid's centre line,
           following the lid's centre sideways.
  Back     follows the back edge of the lid (top row of the silhouette) and
           is hidden wherever the body is. Not allowed when the seeker is
           too tall for it (BACK_MAX_SINK) or, except the Sword, behind a
           deep casing (DEEP).
  Flank    is split into its left and right parts; each keeps the same gap
           to the body as on the Classic, measured on the rows it spans.
  Object   is centred under the seeker's front face; the seeker (base +
           add-ons + eyes) moves up when needed so there are always two empty
           rows above it.
  Eyes     are centred on the open part of the screen (below the glare).
  Picture  shifts sideways by the smallest amount that fits the circle crop.

A combination is allowed only if every pixel stays on the canvas and inside
the circular profile-picture crop, add-ons don't cover the screen, touch the
floating object or touch each other, and back add-ons still show.
"""
import argparse
import csv
import math
import os
import random
import re
from functools import lru_cache

from PIL import Image

import eyes as E
from canvas import Grid
from palette import COLORWAYS
from preview import sheet

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
EXPORT = os.path.join(ROOT, 'layers')
OUT = os.path.join(ROOT, 'renders')

# master colorway the artist painted in -> colorway role
MASTER = {'#6b82b4': 'T', '#6ca886': 'B', '#2b5a48': 'D',
          '#1d3b3a': 'S', '#8fc4a4': 'P', '#e8d28a': 'X'}
GLASS = {(0x3a, 0x75, 0x81), (0x82, 0xb7, 0xb4)}
LID = (0x6b, 0x82, 0xb4)
FACE = '#6ca886'         # casing front colour in the master palette

BASES = {
    'Classic': 'bases1', 'Split Shell': 'bases2', 'Codex Header': 'bases3', 'Hood': 'bases4',
    'Widescreen': 'bases5', 'Tower': 'bases6', 'Porthole': 'bases7', 'Twin Tier': 'bases8',
    'Framed': 'bases9', 'Side Lights': 'bases11', 'Handheld': 'bases12',
    'Radio': 'basesb1', 'Tape Deck': 'basesb2', 'Side Car': 'basesb3', 'Brackets': 'basesb4',
    'Console': 'basesb5',
}
# The Deep Box (bases10) was taken out of the collection: its perspective looked
# odd next to the others. Its hand-tuned rules below are kept in case it returns.
HEAD = {
    'Sonic Emitter': 'hats', 'Rabbit Ears': 'traits-export', 'Dish': 'traits-export2',
    'Heat Sink': 'traits-export3', 'Ice Crystals': 'traits-export4', 'Mushrooms': 'traits-export5',
    'Work Lamp': 'traits-export6', 'Beacon': 'traits-export7', 'Propeller': 'traits-export8',
    'Periscope': 'traits-export9',
}
FLANK = {
    'Solar Wings': 'hands1', 'Thruster Pods': 'hands2', 'Robot Arms': 'hands3',
    'Speakers': 'hands4', 'Plug Cable': 'hands6',
    'Wrench Arm': 'hands7', 'Sword and Shield': 'hands8',
}
BACK = {
    'Battery Pack': 'back1', 'Exhaust Pipes': 'back2', 'Signal Mast': 'back3',
    'Banner': 'back4', 'Tesla Coil': 'back5', 'Coolant Tank': 'back6', 'Sword': 'back7',
}
OBJECTS = {
    'Keyboard': 'inputs1', 'Classic Keyboard': 'inputs2', 'Mouse': 'inputs3',
    'Compact Keyboard': 'inputs4', 'Split Keyboard': 'inputs5', 'Numpad': 'inputs6',
    'Fader Deck': 'inputs7', 'Dial Deck': 'inputs8', 'Gamepad': 'inputs9',
    'Joystick': 'inputs10', 'Codex Slate': 'inputs11', 'Datasette': 'inputs12',
    'Trackball': 'inputs13', 'Floppy Drive': 'inputs14',
}
# Archive: every layer is layers/<folder>/<trait name>.png.
BASES = {k: 'bases/' + k for k in BASES}
HEAD = {k: 'head/' + k for k in HEAD}
FLANK = {k: 'flank/' + k for k in FLANK}
BACK = {k: 'back/' + k for k in BACK}
OBJECTS = {k: 'objects/' + k for k in OBJECTS}
SLOTS = {'Head': HEAD, 'Flank': FLANK, 'Back': BACK}
EXCLUSIVE = [{'Sword and Shield', 'Sword'}]
# flank add-ons drawn behind the casing (hidden wherever the body is)
BEHIND = set()
# hand-tuned nudges on top of the positioning rules
NUDGE = {'Wrench Arm': (-1, 0),
         # as deep as the lid itself: sits at the lid's front edge, not its middle
         'Heat Sink': (0, 2),
         # drawn 2px right of the lid's centre
         'Work Lamp': (-2, 0)}
# Back add-ons hide behind the lid on taller seekers. Most rows of each one
# that may be hidden (compared with the Classic) before it stops reading:
BACK_MAX_SINK = {'Battery Pack': 2, 'Exhaust Pipes': 3, 'Signal Mast': 2, 'Banner': 2,
                 'Tesla Coil': 2, 'Coolant Tank': 3, 'Sword': 3}
# Casings drawn with a long receding depth: nothing behind them but the Sword.
DEEP = {'Deep Box', 'Framed'}
DEEP_OK = {'Sword'}
# Hats with a big footprint need a lid at least this deep (rows) and this
# large (pixels of lid surface). The Heat Sink covers most of a Classic lid.
HAT_MIN_LID = {'Heat Sink': (3, 54)}
# Hand-picked exclusions: hat -> bases it must never appear on.
HAT_NOT_ON = {'Heat Sink': {'Deep Box'}, 'Sonic Emitter': {'Deep Box'},
              'Ice Crystals': {'Deep Box'}}
# The Deep Box recedes up and to the left, so the object under it sits this
# many pixels right of the face's centre to follow that diagonal.
OBJECT_DX = {'Deep Box': 2}
# Hand-picked exclusions: object -> bases it must never appear with.
OBJECT_NOT_ON = {'Codex Slate': {'Framed'}}
# how far the whole picture may slide sideways to fit the circle crop
MAX_PICTURE_SHIFT = 5
# Even-height eyes that sit half a pixel below centre instead of above it.
# (the eight-row eyes lean down too: leaning up they would touch the glare)
EYES_LEAN_DOWN = {'Dots', 'Squint', 'Curious', 'Snowflake'}
# Bases where every even-height eye leans down: the glare sits high on the
# round Porthole glass, so eyes leaning up look too close to it.
BASES_EYES_LEAN_DOWN = {'Porthole'}
# chance a slot stays empty
# Hand-picked colour fixes: (add-on, colorway) -> {role: role to use instead}.
# The Solar Wings' frame and grid are the plate colour (P) around fixed teal
# cells; Deep Teal's plate IS that teal, so the grid vanished. There the frame
# takes the lid colour (T) instead.
ROLE_SWAP = {('Solar Wings', 'Deep Teal'): {'P': 'T'}}
EMPTY = {'Head': 0.5, 'Flank': 0.5, 'Back': 0.55}

REF = 'Classic'
KEYS = ['Base', 'Colorway', 'Eyes', 'Floating Object', 'Head', 'Flank', 'Back']
CX = CY = 26.5
RADIUS = 26.5
OBJECT_GAP = 2           # empty rows between seeker and floating object


def in_circle(x, y):
    return (x - CX) ** 2 + (y - CY) ** 2 <= RADIUS ** 2


def _hex(p):
    return '#%02x%02x%02x' % p[:3]


@lru_cache(maxsize=None)
def layer(stem):
    """{(x, y): rgba} of an export PNG, isolated single pixels removed."""
    im = Image.open(os.path.join(EXPORT, stem + '.png')).convert('RGBA')
    px = {(x, y): im.getpixel((x, y)) for y in range(im.height) for x in range(im.width)
          if im.getpixel((x, y))[3]}
    return {p: c for p, c in px.items()
            if any((p[0] + dx, p[1] + dy) in px
                   for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy)}


def shift(px, dx, dy):
    return {(x + dx, y + dy): c for (x, y), c in px.items()}


# ------------------------------------------------------------ base geometry

class Base:
    def __init__(self, name):
        self.name = name
        self.px = layer(BASES[name])
        pts = set(self.px)
        vol = set(pts)
        for y in range(54):
            xs = [x for x, yy in pts if yy == y]
            if xs:
                vol |= {(x, y) for x in range(min(xs), max(xs) + 1)}
        for x in range(54):
            ys = [y for xx, y in pts if xx == x]
            if ys:
                vol |= {(x, y) for y in range(min(ys), max(ys) + 1)}
        self.vol = vol
        self.top = min(y for _, y in pts)
        self.bottom = max(y for _, y in pts)
        row = [x for x, y in pts if y == self.top]
        self.back_x = sum(row) / len(row)
        lid = [p for p, c in self.px.items() if c[:3] == LID]
        # the main lid surface: rows at least half as wide as the widest one
        # (leaves out small top faces elsewhere, like a side module's)
        rows = {}
        for x, y in lid:
            rows[y] = rows.get(y, 0) + 1
        main = {y for y, n in rows.items() if n >= 0.5 * max(rows.values())}
        lid = [p for p in lid if p[1] in main]
        self.lid = (sum(x for x, _ in lid) / len(lid), sum(y for _, y in lid) / len(lid))
        self.lid_front = max(main)
        self.lid_depth = len(main)
        self.lid_area = len(lid)
        self.lid_rows = {y: (min(x for x, yy in lid if yy == y), max(x for x, yy in lid if yy == y))
                         for y in main}
        self.left = {y: min(x for x, yy in vol if yy == y) for y in {y for _, y in vol}}
        self.right = {y: max(x for x, yy in vol if yy == y) for y in {y for _, y in vol}}
        face = [x for (x, y), c in self.px.items() if _hex(c) == FACE]
        self.face_c = (min(face) + max(face)) / 2
        self.screen = self._screen()
        # open part of the screen: rows / columns at least 70% as full as the
        # fullest one (drops the slivers beside the glare)
        rows, cols = {}, {}
        for x, y in self.screen:
            rows[y] = rows.get(y, 0) + 1
            cols[x] = cols.get(x, 0) + 1
        ry = [y for y, v in rows.items() if v >= 0.7 * max(rows.values())]
        cx = [x for x, v in cols.items() if v >= 0.7 * max(cols.values())]
        self.eye = (min(cx), min(ry), max(cx), max(ry))
        self.eye_c = ((min(cx) + max(cx)) / 2, (min(ry) + max(ry)) / 2)

    def _screen(self):
        """The black screen interior: the largest patch of black pixels inside
        the glass ring (other glassy details, like tape reels, have their own
        smaller black windows)."""
        glass = [p for p, c in self.px.items() if c[:3] in GLASS]
        gx0, gx1 = min(x for x, _ in glass), max(x for x, _ in glass)
        gy0, gy1 = min(y for _, y in glass), max(y for _, y in glass)
        black = {p for p, c in self.px.items()
                 if c[:3] == (0, 0, 0) and gx0 < p[0] < gx1 and gy0 < p[1] < gy1}
        best, seen = set(), set()
        for p in black:
            if p in seen:
                continue
            comp, stack = {p}, [p]
            seen.add(p)
            while stack:
                x, y = stack.pop()
                for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if q in black and q not in seen:
                        seen.add(q)
                        comp.add(q)
                        stack.append(q)
            if len(comp) > len(best):
                best = comp
        return best


@lru_cache(maxsize=None)
def base(name):
    return Base(name)


# ------------------------------------------------------------ placement

def _split(px):
    """Left and right parts of a flank layer (either may be empty)."""
    left = {p: c for p, c in px.items() if p[0] < 27}
    right = {p: c for p, c in px.items() if p[0] >= 27}
    return left, right


def _gap(part, b, side):
    """Smallest horizontal gap between a flank part and the body, over the
    rows they share (None if they share none)."""
    gaps = []
    for y in {y for _, y in part}:
        if y not in b.left:
            continue
        xs = [x for x, yy in part if yy == y]
        gaps.append(b.left[y] - max(xs) if side == 'L' else min(xs) - b.right[y])
    return min(gaps) if gaps else None


def slot_of(addon):
    return next(s for s, d in SLOTS.items() if addon in d)


@lru_cache(maxsize=None)
def placed(addon, base_name, mdy=0):
    """{(x, y): rgba} of an add-on on `base_name`, for a seeker shifted
    vertically by `mdy` (final canvas coordinates)."""
    ref, b = base(REF), base(base_name)
    slot = slot_of(addon)
    px = layer(SLOTS[slot][addon])
    if slot == 'Head':
        # stands on the lid: bottom row one above the lid's centre line (the
        # artist top-aligned the hats on the canvas, so their own y is ignored)
        bottom = max(y for _, y in px)
        target = _rnd(b.lid[1]) - 1 + mdy
        nx, ny = NUDGE.get(addon, (0, 0))
        # ...and never lower than the row above the lid's front edge
        seat = min(_rnd(b.lid[1]) - 1 + ny, b.lid_front - 1)
        dx = round(b.lid[0] - ref.lid[0]) + nx
        # its bottom row has to rest on the lid: slide sideways if that seats it
        foot = [x for x, y in px if y == bottom]
        dx += _seat_shift(min(foot) + dx, max(foot) + dx, b.lid_rows.get(seat))
        return shift(px, dx, seat + mdy - bottom)
    if slot == 'Back':
        # follows the lid's back edge down, but never rises above where the
        # artist drew it: on taller seekers more of it hides behind the lid
        return shift(px, round(b.back_x - ref.back_x), max(b.top + mdy - ref.top, 0))
    out = {}
    for part, side in zip(_split(px), 'LR'):
        if not part:
            continue
        g_ref, g_new = _gap(part, ref, side), _gap(part, b, side)
        dx = 0 if g_ref is None or g_new is None else g_ref - g_new
        out.update(shift(part, -dx if side == 'L' else dx, mdy))
    return shift(out, *NUDGE.get(addon, (0, 0)))


def _seat_shift(x0, x1, row):
    """Smallest sideways move (up to 2px) that puts a hat's bottom row x0..x1
    on the lid row (lx0, lx1), keeping 1px clear of the lid's right edge."""
    if not row:
        return 0
    for d in (0, -1, 1, -2, 2):
        if row[0] <= x0 + d and x1 + d <= row[1] - 1:
            return d
    return 0


def hat_seated(addon, base_name):
    """True if the hat's bottom row rests on the lid."""
    b = base(base_name)
    px = placed(addon, base_name)
    bottom = max(y for _, y in px)
    row = b.lid_rows.get(bottom)
    foot = [x for x, y in px if y == bottom]
    return bool(row) and row[0] <= min(foot) and max(foot) <= row[1]


def body(base_name, mdy=0):
    b = base(base_name)
    return {(x, y + mdy) for x, y in b.vol}


@lru_cache(maxsize=None)
def visible(addon, base_name, mdy=0):
    px = placed(addon, base_name, mdy)
    if slot_of(addon) == 'Back' or addon in BEHIND:
        vol = body(base_name, mdy)
        return {p: c for p, c in px.items() if p not in vol}
    return px


def _halo(pts):
    return {(x + dx, y + dy) for x, y in pts for dx in (-1, 0, 1) for dy in (-1, 0, 1)}


@lru_cache(maxsize=None)
def object_px(name):
    return layer(OBJECTS[name])


def _rnd(v):
    return int(math.floor(v + 0.5))


def object_dx(t):
    """Centre the object under the seeker's front face (the casing's left
    flank is a dark void, so the face is what reads as the body)."""
    px = object_px(t['Floating Object'])
    xs = [x for x, _ in px]
    return _rnd(base(t['Base']).face_c - (min(xs) + max(xs)) / 2) + OBJECT_DX.get(t['Base'], 0)


@lru_cache(maxsize=None)
def object_room(name, dx):
    """How far the object can move down and stay inside the circle."""
    px = shift(object_px(name), dx, 0)
    return max([k for k in range(0, 6) if all(in_circle(x, y + k) for x, y in px)] or [0])


def layout(t):
    """(seeker dy, object dx, object dy): keep OBJECT_GAP empty rows between
    seeker and object, moving the object down first, then the seeker up."""
    b = base(t['Base'])
    if not t.get('Floating Object'):         # nothing below: centre the seeker
        return _rnd(CY - (b.top + b.bottom) / 2), 0, 0
    odx = object_dx(t)
    top = min(y for _, y in object_px(t['Floating Object']))
    need = b.bottom + OBJECT_GAP + 1 - top
    if need <= 0:
        return 0, odx, 0
    ody = min(need, object_room(t['Floating Object'], odx))
    return -(need - ody), odx, ody


@lru_cache(maxsize=None)
def eye_px(name, base_name):
    """Eye glyph centred on the open part of this base's screen, clipped to
    the black screen pixels."""
    b = base(base_name)
    g = E.EYES[name]()
    pts = {(x, y): g.get(x, y) for y in range(54) for x in range(54) if g.get(x, y) != '.'}
    xs = [x for x, _ in pts]
    ys = [y for _, y in pts]
    dx = _rnd(b.eye_c[0] - (min(xs) + max(xs)) / 2)
    # The black screen area is 9 rows tall, so a glyph of even height can't
    # sit exactly on the centre row: it leans half a pixel up, or down for
    # the eyes listed in EYES_LEAN_DOWN (chosen by eye).
    v = b.eye_c[1] - (min(ys) + max(ys)) / 2
    down = name in EYES_LEAN_DOWN or base_name in BASES_EYES_LEAN_DOWN
    dy = _rnd(v) if down else math.ceil(v - 0.5)
    out = {}
    for (x, y), role in pts.items():
        p = (x + dx, y + dy)
        if p in b.screen:
            out[p] = E.PAL[role]
    return out


@lru_cache(maxsize=None)
def addon_fits(addon, base_name, mdy=0):
    """Reason the add-on can't go on this base, or None (circle crop is
    checked on the whole picture)."""
    b = base(base_name)
    vis = visible(addon, base_name, mdy)
    x0, y0, x1, y1 = b.eye
    if any(x0 - 1 <= x <= x1 + 1 and y0 + mdy - 1 <= y <= y1 + mdy + 1 for x, y in vis):
        return 'covers the screen'
    if slot_of(addon) == 'Head':
        if base_name in HAT_NOT_ON.get(addon, ()):
            return 'not on this base'
        depth, area = HAT_MIN_LID.get(addon, (0, 0))
        if b.lid_depth < depth or b.lid_area < area:
            return 'lid too small'
        if not hat_seated(addon, base_name):
            return 'does not sit on the lid'
    if slot_of(addon) == 'Back':
        if base_name in DEEP and addon not in DEEP_OK:
            return 'not behind a deep casing'
        sink = base(REF).top - (b.top + mdy)
        if sink > BACK_MAX_SINK[addon]:
            return 'seeker too tall'
        if len(vis) < 0.6 * len(visible(addon, REF)):
            return 'mostly hidden behind the body'
    return None


def _fit_options(pref):
    """(picture dx, object dx) candidates, smallest picture shift first."""
    # the object always stays where it belongs under the seeker; only the
    # whole picture may slide. If that can't fit, the combination is not allowed.
    return sorted(((sx, pref) for sx in range(-MAX_PICTURE_SHIFT, MAX_PICTURE_SHIFT + 1)),
                  key=lambda o: (abs(o[0]), o[0]))


@lru_cache(maxsize=None)
def fit(base_name, obj, picks):
    """(picture dx, object dx) that keeps every pixel on the canvas and inside
    the circle crop, or None."""
    t = {'Base': base_name, 'Floating Object': obj}
    mdy, pref, ody = layout(t)
    seeker = {(x, y + mdy) for x, y in base(base_name).px}
    for a in picks:
        seeker |= set(visible(a, base_name, mdy))
    objpx = [(x, y + ody) for x, y in object_px(obj)] if obj else []

    def ok(x, y):
        return 0 <= x < 54 and 0 <= y < 54 and in_circle(x, y)

    for sx, odx in _fit_options(pref):
        if all(ok(x + sx, y) for x, y in seeker) and \
                all(ok(x + odx + sx, y) for x, y in objpx):
            return sx, odx
    return None


def scene_fit(t):
    picks = tuple(sorted(t[s] for s in SLOTS if t.get(s)))
    return fit(t['Base'], t.get('Floating Object'), picks)


def check(t):
    """None if the full combination works, else the reason."""
    mdy, odx, ody = layout(t)
    picks = [t[s] for s in SLOTS if t.get(s)]
    for a in picks:
        r = addon_fits(a, t['Base'], mdy)
        if r:
            return f'{a}: {r}'
    for i, p in enumerate(picks):
        for q in picks[i + 1:]:
            if {p, q} in EXCLUSIVE:
                return f'{p} + {q} not allowed together'
            if _halo(visible(p, t['Base'], mdy)) & set(visible(q, t['Base'], mdy)):
                return f'{p} touches {q}'
    if t['Base'] in OBJECT_NOT_ON.get(t.get('Floating Object'), ()):
        return 'object not allowed with this base'
    f = scene_fit(t)
    if f is None:
        return 'does not fit the circle crop'
    if not t.get('Floating Object'):
        return None
    obj = set(shift(object_px(t['Floating Object']), f[1], ody))
    seeker = body(t['Base'], mdy)
    for a in picks:
        seeker |= set(visible(a, t['Base'], mdy))
    if _halo(seeker) & obj:
        return 'touches the floating object'
    return None


# ------------------------------------------------------------ rendering

def recolor(px, colorway, part=None):
    """Master colours -> the colorway's. `part` is the trait being painted,
    for the hand-picked exceptions in ROLE_SWAP."""
    pal = COLORWAYS[colorway]
    swap = ROLE_SWAP.get((part, colorway), {})
    out = {}
    for p, c in px.items():
        role = MASTER.get(_hex(c))
        out[p] = pal[swap.get(role, role)] if role else _hex(c)
    return out


def paint(im, px, sx=0):
    for (x, y), c in px.items():
        x += sx
        if 0 <= x < 54 and 0 <= y < 54:
            if isinstance(c, str):
                c = tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) + (255,)
            im.putpixel((x, y), c)


def compose(t, background=(0, 0, 0, 255), eyes=True, eye_px_override=None):
    """Render a seeker. Pass background=(0, 0, 0, 0) for a transparent one,
    eyes=False for a blank screen, eye_px_override={(x, y): colour} to show
    something else on the screen (before the seeker's shift)."""
    b = base(t['Base'])
    mdy, _, ody = layout(t)
    sx, odx = scene_fit(t) or (0, 0)
    cw = t['Colorway']
    im = Image.new('RGBA', (54, 54), background)
    if t.get('Floating Object'):
        paint(im, shift(object_px(t['Floating Object']), odx, ody), sx)
    behind = [t['Back']] if t.get('Back') else []
    if t.get('Flank') in BEHIND:
        behind.append(t['Flank'])
    for a in behind:
        paint(im, recolor(visible(a, t['Base'], mdy), cw, a), sx)
    paint(im, shift(recolor(b.px, cw), 0, mdy), sx)
    for slot in ('Flank', 'Head'):
        a = t.get(slot)
        if a and a not in BEHIND:
            paint(im, recolor(placed(a, t['Base'], mdy), cw, a), sx)
    if eye_px_override is not None:
        paint(im, shift(eye_px_override, 0, mdy), sx)
    elif eyes:
        paint(im, shift(eye_px(t['Eyes'], t['Base']), 0, mdy), sx)
    return im


def layers(t):
    """The seeker as separate parts, in paint order (first = furthest back):
    [(part, {(x, y): '#rrggbb'})] with part one of 'Floating Object', 'Back',
    'Base', 'Flank', 'Head', 'Eyes'. Pixels are in final canvas coordinates
    and already recoloured, so painting them in order gives compose(t). Empty
    slots are left out. For animating parts on their own."""
    b = base(t['Base'])
    mdy, _, ody = layout(t)
    sx, odx = scene_fit(t) or (0, 0)
    cw = t['Colorway']

    def final_px(px):
        out = {}
        for (x, y), c in px.items():
            if 0 <= x + sx < 54 and 0 <= y < 54:
                out[(x + sx, y)] = c if isinstance(c, str) else _hex(c)
        return out

    out = []
    if t.get('Floating Object'):
        out.append(('Floating Object', final_px(shift(object_px(t['Floating Object']), odx, ody))))
    if t.get('Back'):
        out.append(('Back', final_px(recolor(visible(t['Back'], t['Base'], mdy), cw, t['Back']))))
    out.append(('Base', final_px(shift(recolor(b.px, cw), 0, mdy))))
    for slot in ('Flank', 'Head'):
        if t.get(slot):
            out.append((slot, final_px(recolor(placed(t[slot], t['Base'], mdy), cw, t[slot]))))
    out.append(('Eyes', final_px(shift(eye_px(t['Eyes'], t['Base']), 0, mdy))))
    return out


def screen_px(t):
    """The black screen pixels of the seeker in final canvas coordinates
    (where eyes may be drawn), and the rectangle the eyes are centred on."""
    b = base(t['Base'])
    mdy = layout(t)[0]
    sx = (scene_fit(t) or (0, 0))[0]
    x0, y0, x1, y1 = b.eye
    return ({(x + sx, y + mdy) for x, y in b.screen},
            (x0 + sx, y0 + mdy, x1 + sx, y1 + mdy))


# ------------------------------------------------------------ dormant art
# A seeker that is not charged yet ("uncharged", "dormant"): its screen shows
# a battery instead of its eyes, the whole seeker is darkened, and it sits on
# a faint lit circle. Six stages by charge: the battery fills and the seeker
# brightens; the background is the same at every stage. Assets: charge/ (the
# battery icons) and NewUncharged/ (background-uncharged1 and the overlays).

STAGES = 6
CHARGE_DIR = os.path.join(ROOT, 'layers', 'uncharged')
UNCHARGED_DIR = os.path.join(ROOT, 'layers', 'uncharged')
THRESHOLD = 9000


def file_number(index):
    """The number in an artwork's file names. Artwork 0's files are numbered
    2222 (a file named 0 could not be uploaded); the on-chain renderer does the
    same. Every other artwork uses its own index."""
    return int(index) or 2222


def stage_of(charge):
    """Dormant stage 1-6 for a charge of 0-9,000 (six equal bands)."""
    return min(int(charge * STAGES // THRESHOLD), STAGES - 1) + 1


@lru_cache(maxsize=None)
def charge_px(stage, base_name):
    """The battery icon for a stage, centred on the screen like an eye."""
    b = base(base_name)
    im = Image.open(os.path.join(CHARGE_DIR, f'battery{stage}.png')).convert('RGBA')
    pts = {(x, y): im.getpixel((x, y)) for y in range(im.height) for x in range(im.width)
           if im.getpixel((x, y))[3]}
    xs = [x for x, _ in pts]
    ys = [y for _, y in pts]
    dx = _rnd(b.eye_c[0] - (min(xs) + max(xs)) / 2)
    # four rows tall in a nine-row screen: like the even-height eyes it leans
    # up (the glare makes the glass read taller than its black part), except
    # on the bases where eyes lean down
    v = b.eye_c[1] - (min(ys) + max(ys)) / 2
    dy = _rnd(v) if base_name in BASES_EYES_LEAN_DOWN else math.ceil(v - 0.5)
    return {(x + dx, y + dy): c for (x, y), c in pts.items() if (x + dx, y + dy) in b.screen}


@lru_cache(maxsize=None)
def shade_alpha(stage):
    """How black the overlay is at this stage, 0-255 (one flat black layer)."""
    im = Image.open(os.path.join(UNCHARGED_DIR, f'shade{stage}.png')).convert('RGBA')
    alphas = {p[3] for p in im.getdata()}
    assert len(alphas) == 1, alphas
    return alphas.pop()


@lru_cache(maxsize=None)
def dormant_background():
    return Image.open(os.path.join(UNCHARGED_DIR, 'background.png')).convert('RGBA')


def compose_dormant(t, stage, shade=True):
    """The dormant picture of a seeker at a charge stage (1-6). The overlay
    darkens every part of the seeker, the battery too, but never the
    background. shade=False leaves the overlay out."""
    fg = compose(t, background=(0, 0, 0, 0), eye_px_override=charge_px(stage, t['Base']))
    keep = 255 - (shade_alpha(stage) if shade else 0)
    px = fg.load()
    for y in range(54):
        for x in range(54):
            r, g, bl, a = px[x, y]
            if a:
                px[x, y] = (r * keep // 255, g * keep // 255, bl * keep // 255, a)
    im = dormant_background().copy()
    im.alpha_composite(fg)
    return im


# ------------------------------------------------------------ sampling

def roll(rng):
    while True:
        t = {'Base': rng.choice(list(BASES)),
             'Colorway': rng.choice(list(COLORWAYS)),
             'Eyes': rng.choice(list(E.EYES)),
             'Floating Object': rng.choice(list(OBJECTS))}
        if check(t):
            continue
        slots = list(SLOTS)
        rng.shuffle(slots)
        for s in slots:
            t[s] = None
            if rng.random() < EMPTY[s]:
                continue
            opts = list(SLOTS[s])
            rng.shuffle(opts)
            for a in opts:
                t[s] = a
                if check(t) is None:
                    break
                t[s] = None
        return t


def report():
    lines = []
    for s, d in SLOTS.items():
        for a in d:
            no = {}
            for n in BASES:
                rs = [check({'Base': n, 'Colorway': 'Ember', 'Eyes': 'Dots',
                             'Floating Object': o, s: a}) for o in OBJECTS]
                ok = sum(r is None for r in rs)
                if ok < len(rs):
                    no[n] = f'{ok}/{len(rs)} objects; ' + next(r for r in rs if r)
            full = sum(1 for n in BASES if n not in no)
            lines.append(f'{s:5} {a:17} {full:2}/{len(BASES)} bases with every object  '
                         + ', '.join(f'{k} ({v})' for k, v in no.items()))
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--grids', type=int, default=3)
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--report', action='store_true')
    a = ap.parse_args()
    if a.report:
        print(report())
        return
    os.makedirs(os.path.join(OUT, 'previews'), exist_ok=True)
    rng = random.Random(a.seed)
    seen, rows = set(), []
    for g in range(a.grids):
        items = []
        while len(items) < 64:
            t = roll(rng)
            key = tuple(sorted((k, v or '') for k, v in t.items()))
            if key in seen:
                continue
            seen.add(key)
            items.append(('', compose(t)))
            rows.append([f'{g + 1}', f'{len(items)}'] + [t.get(k) or 'None' for k in KEYS])
        path = os.path.join(OUT, 'previews', f'grid_{g + 1}.png')
        sheet(items, path, cols=8, scale=4, label=False)
        print(path)
    with open(os.path.join(OUT, 'previews', 'grids.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['Grid', 'Cell (row by row)'] + KEYS)
        w.writerows(rows)


if __name__ == '__main__':
    main()
