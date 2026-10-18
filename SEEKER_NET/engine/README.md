# engine

The code that drew the collection, copied from the project's generator. Only the
file paths were changed, and the eyes are read from `layers/eyes/` instead of being
drawn in code. `seeker.py` uses it; you never need to run these files directly.

- `final.py`: the placement rules and the still pictures (activated and uncharged)
- `animate_collection.py` + `animkit.py`: the activated animations
- `eyes.py`, `canvas.py`, `palette.py`, `preview.py`: eyes, pixel grid, colours, preview sheets
