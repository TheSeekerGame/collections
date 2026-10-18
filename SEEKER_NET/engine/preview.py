"""Contact-sheet helper: upscaled grids of layers on black (aspect preserved)."""
from PIL import Image, ImageDraw


def sheet(items, path, cols=5, scale=6, label=True):
    """items: list of (name, RGBA image); all images the same size."""
    w, h = items[0][1].size
    cw, ch = w * scale, h * scale
    pad = 18 if label else 4
    rows = (len(items) + cols - 1) // cols
    out = Image.new('RGB', (cols * (cw + 4), rows * (ch + pad)), (24, 24, 28))
    d = ImageDraw.Draw(out)
    for i, (name, im) in enumerate(items):
        bg = Image.new('RGBA', im.size, (0, 0, 0, 255))
        bg.alpha_composite(im)
        x, y = (i % cols) * (cw + 4), (i // cols) * (ch + pad)
        out.paste(bg.convert('RGB').resize((cw, ch), Image.NEAREST), (x, y))
        if label:
            d.text((x + 4, y + ch + 3), name, fill=(200, 200, 210))
    out.save(path)
