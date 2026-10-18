"""Tiny pixel canvas working in *role letters* rather than colours.

Every asset is authored as a 54x54 grid of single-character roles. A role is
resolved to a colour at render time, either from a colorway (casing roles) or
from a fixed palette. '.' is always transparent.
"""
from PIL import Image

SIZE = 54


def hex2rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


class Grid:
    def __init__(self, rows=None, y0=0):
        self.px = [['.'] * SIZE for _ in range(SIZE)]
        self.oob = 0          # writes that fell off the canvas
        if rows:
            self.stamp(rows, 0, y0)

    def copy(self):
        g = Grid()
        g.px = [r[:] for r in self.px]
        g.oob = self.oob
        return g

    def get(self, x, y):
        if 0 <= x < SIZE and 0 <= y < SIZE:
            return self.px[y][x]
        return '.'

    def set(self, x, y, c):
        if 0 <= x < SIZE and 0 <= y < SIZE:
            self.px[y][x] = c
        elif c != '.':
            self.oob += 1

    def pixels(self):
        return {(x, y) for y in range(SIZE) for x in range(SIZE) if self.px[y][x] != '.'}

    def pts(self, c, *xy):
        for x, y in xy:
            self.set(x, y, c)

    def hline(self, x0, x1, y, c):
        for x in range(x0, x1 + 1):
            self.set(x, y, c)

    def vline(self, x, y0, y1, c):
        for y in range(y0, y1 + 1):
            self.set(x, y, c)

    def rect(self, x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            self.hline(x0, x1, y, c)

    def stamp(self, rows, x0, y0, skip='.'):
        """Paste an ASCII block; `skip` chars are left untouched.
        Use '_' inside a block to force-clear a pixel to transparent."""
        for dy, row in enumerate(rows):
            for dx, c in enumerate(row):
                if c in skip:
                    continue
                self.set(x0 + dx, y0 + dy, '.' if c == '_' else c)

    def replace(self, old, new, region=None):
        x0, y0, x1, y1 = region or (0, 0, SIZE - 1, SIZE - 1)
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                if self.px[y][x] == old:
                    self.px[y][x] = new

    def render(self, palette):
        im = Image.new('RGBA', (SIZE, SIZE), (0, 0, 0, 0))
        for y in range(SIZE):
            for x in range(SIZE):
                c = self.px[y][x]
                if c == '.':
                    continue
                if c not in palette:
                    raise KeyError(f'role {c!r} at {x},{y} has no colour')
                im.putpixel((x, y), hex2rgb(palette[c]) + (255,))
        return im
