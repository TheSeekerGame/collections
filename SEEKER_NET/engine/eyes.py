"""Eyes traits: glyphs shown on the screen.

Screen interior (shared by every casing) is x24-34, y23-31. Eyes are clipped
to it, so they can never spill onto the glass frame or glare.
"""
import os
from PIL import Image
from canvas import Grid

ROOT = os.path.join(os.path.dirname(__file__), '..', 'references')
INTERIOR = (24, 23, 34, 31)
CENTER_Y = 26.5          # where the reference seekers centre their eyes
EYE_SET_DX = 7           # artist eye set is drawn ~7px left of our screen

PAL = {
    'W': '#ffffff',
    # ref 1 orb
    'j': '#eaf2f4', 'h': '#cadbe1', 'i': '#c1cfd6',
    # ref 2 orb
    'p': '#cbdede', 'q': '#a3b7b1', 'u': '#92a9a6',
    # tinted glyphs
    'G': '#82b7b4', 'X': '#a2324e',
}


def _grid(rows, x, y):
    g = Grid()
    g.stamp(rows, x, y)
    return g


def from_eye_set(n):
    """Repurpose an eye from the artist's other collection: white pixels
    only (the black drop shadows are dropped), mirrored to face our way."""
    im = Image.open(os.path.join(ROOT, 'Eyes', f'eye{n}.png')).convert('RGBA')
    white = [(x, y) for y in range(54) for x in range(54)
             if im.getpixel((x, y)) == (255, 255, 255, 255)]
    x0 = min(x for x, _ in white)
    x1 = max(x for x, _ in white)
    y0 = min(y for _, y in white)
    y1 = max(y for _, y in white)
    top = max(24, int(CENTER_Y - (y1 - y0) / 2))   # keep 1px clear of glare
    g = Grid()
    for x, y in white:
        g.set(x0 + x1 - x + EYE_SET_DX, y - y0 + top, 'W')
    return g


# ---------------------------------------------- extracted from the references

def orb():          # ref 1
    return _grid(['.hhii.',
                  'jjjjhh',
                  'jjjjjh',
                  'jjjjjh',
                  'jjjjjh',
                  '.hhhh.'], 27, 24)


def pale_orb():     # ref 2
    return _grid(['.pppp.',
                  'pppppp',
                  'qqqqqq',
                  'qqqqqq',
                  'uuqqqq',
                  '.uuqq.'], 27, 24)


def theorem():      # ref 5
    return _grid(['WWW.WW',
                  'WWW.WW',
                  '..W.W.',
                  '..W.W.',
                  '.WW.W.',
                  '.WW.W.'], 27, 24)


def frown():        # ref 6
    return _grid(['.WWWWWW.',
                  'WW....WW',
                  'WW....WW'], 26, 25)


def content():      # ref 7 (moved onto the shared screen grid)
    return _grid(['...W..W...',
                  '..W....W..',
                  'WWW....WWW',
                  '..W....W..',
                  '...WWWW...'], 25, 25)


def dots():         # ref 4
    return _grid(['WW....WW',
                  'WW....WW'], 26, 26)


def happy():
    """The Cleaner promo's happy eyes: each Dots eye becomes a ^."""
    return _grid(['.WW....WW.',
                  'W..W..W..W'], 25, 26)


def flatline():     # ref 3
    return _grid(['WWWWWWWW',
                  'WWWWWWWW'], 26, 26)


# --------------------------------------------------------------- new, lore

def pulse():
    """'Pulses. Frequencies clashing in perfect harmony.'"""
    return _grid(['....W......',
                  '....W......',
                  '...W.W.....',
                  'WWW..W..WWW',
                  '.....W.W...',
                  '......W....'], 24, 24)


def reticle():
    """Codex scan lock."""
    return _grid(['WW.....WW',
                  'W.......W',
                  '.........',
                  '....W....',
                  '.........',
                  'W.......W',
                  'WW.....WW'], 25, 24)


def mycelia():
    """Fractal structures you recognise from mycelia diagrams."""
    return _grid(['W...W...W',
                  '.W..W..W.',
                  '..W.W.W..',
                  '...WWW...',
                  '....W....',
                  '...W.W...',
                  '..W...W..'], 25, 24)


def sigil():
    """The Theorem's mark."""
    return _grid(['....W....',
                  '...W.W...',
                  '..W...W..',
                  '.W..W..W.',
                  'W.......W',
                  'WWWWWWWWW'], 25, 24)


EYES = {
    # from the reference seekers
    'Orb': orb,
    'Theorem': theorem,
    'Frown': frown,
    'Seeker': content,
    'Dots': dots,
    'Flatline': flatline,
    # repurposed from the artist's eye set
    'Lens': lambda: from_eye_set(7),
    'Squint': lambda: from_eye_set(8),
    'Lidded': lambda: from_eye_set(18),
    'Wary': lambda: from_eye_set(22),
    'Slant': lambda: from_eye_set(23),
    'Dome': lambda: from_eye_set(29),
    'Curious': lambda: from_eye_set(33),
    'Visor': lambda: from_eye_set(35),
    'Wide': lambda: from_eye_set(37),
    # new
    'Pulse': pulse,
    'Reticle': reticle,
    'Mycelia': mycelia,
    'Sigil': sigil,
    'Happy': happy,
    # the rest of the artist's eye set. Left out: 5 (same as Theorem); 1, 3, 13
    # (ten rows tall: the open screen is nine rows); and the ones the user
    # rejected: 11 (Ring), 2, 4, 6, 10, 12, 14, 19, 28, 30, 31, 34
    'Glitch': lambda: from_eye_set(9),
    'Snowflake': lambda: from_eye_set(15),
    'Keyhole': lambda: from_eye_set(16),
    'Tangle': lambda: from_eye_set(17),
    'Steady': lambda: from_eye_set(20),
    'Scowl': lambda: from_eye_set(21),
    'Peek': lambda: from_eye_set(24),
    'Shutter': lambda: from_eye_set(25),
    'Dashes': lambda: from_eye_set(26),
    'Blocks': lambda: from_eye_set(27),
    'Beans': lambda: from_eye_set(32),
    'Slit': lambda: from_eye_set(36),
}


# Archive: every eye is a picture, layers/eyes/<name>.png: the glyphs
# defined above, drawn in the PAL colours. The pictures are what is used.
_EYE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'layers', 'eyes')
_ROLE = {tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)): role for role, h in PAL.items()}
assert len(_ROLE) == len(PAL), 'every eye colour must stand for one role'


def _eye_layer(name):
    im = Image.open(os.path.join(_EYE_DIR, name + '.png')).convert('RGBA')
    g = Grid()
    for y in range(54):
        for x in range(54):
            p = im.getpixel((x, y))
            if p[3]:
                g.set(x, y, _ROLE[p[:3]])
    return g


EYES = {name: (lambda n=name: _eye_layer(n)) for name in EYES}


def render(name, rect=INTERIOR, casing=None):
    """Draw eyes centred in `rect` (a casing's glass), clipped to it and to
    the casing's empty glass pixels."""
    src = EYES[name]()
    x0, y0, x1, y1 = rect
    bx0, by0, bx1, by1 = INTERIOR
    dx = (x0 + x1) // 2 - (bx0 + bx1) // 2
    dy = (y0 + y1) // 2 - (by0 + by1) // 2
    g = Grid()
    for y in range(54):
        for x in range(54):
            c = src.get(x, y)
            if c == '.':
                continue
            tx, ty = x + dx, y + dy
            if not (x0 <= tx <= x1 and y0 <= ty <= y1):
                continue
            if casing is not None and casing.get(tx, ty) != '.':
                continue
            g.set(tx, ty, c)
    return g.render(PAL)
