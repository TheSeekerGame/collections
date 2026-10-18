"""Colour roles.

FIXED roles are identical across every seeker in the reference art (rim
lights, screen glass, glare). COLORWAY roles are what changes from seeker to
seeker:

  T  lid / top face          B  front body
  D  body shadow (left bevel, under-lid, bottom)
  S  screen-inset shadow     P  secondary plate (camo, header, stripes)
  X  indicator light
"""

FIXED = {
    'R': '#d5f8fc',  # top rim highlight
    'A': '#8ea6db',  # rim accent / corner light
    'L': '#6c78a2',  # left rim light
    'K': '#48557e',  # bottom rim light
    'G': '#82b7b4',  # screen glass highlight
    'I': '#3a7581',  # screen glass shade
    'W': '#ffffff',  # glare / glyphs
    'Z': '#000000',  # explicit black (cuts, holes)
    # extras for special casings (all pulled from the reference art)
    'c': '#cadbe1',  # ice mid
    'e': '#eaf2f4',  # ice light
    'v': '#8db6d1',  # ice blue
    'm': '#e3e3b7',  # fungus cap / brass highlight
    'n': '#997c5a',  # fungus gill / stalk shade
    'k': '#dbede3',  # fungus stalk
    'o': '#c59154',  # brass
    'b': '#905937',  # brass shade
    'r': '#a2324e',  # red light
    'y': '#661e25',  # deep maroon
    'g': '#5daa99',  # spore glow
    'u': '#e3e3b7',  # mushroom cap light
    'h': '#b9a87b',  # mushroom cap
    'j': '#5f4754',  # mushroom gills / stalk shade
    'q': '#dbede3',  # mushroom stalk
    # Robin Hood kit
    't': '#6b8e5e',  # felt light
    's': '#4e6845',  # felt
    'z': '#214e3f',  # felt shade
    'l': '#803e31',  # leather
    'w': '#b9a87b',  # wood light
    'd': '#5f4754',  # wood / leather shade
    # gunmetal (sci-fi weapons), greys taken from the reference slate tones
    'a': '#a3b7b1',  # alloy light
    'f': '#788982',  # alloy
    'x': '#485f67',  # alloy shade
}

# name: (T, B, D, S, P, X)
_CW = {
    # --- lifted directly from the reference seekers ---
    'Ember':      ('#87789b', '#c59154', '#4f335d', '#661e25', '#905937', '#a2324e'),  # ref 5
    'Moss':       ('#6b82b4', '#6ca886', '#214e3f', '#214e3f', '#5daa99', '#d5f8fc'),  # ref 6
    'Obsidian':   ('#596d9b', '#323f4b', '#0f2a3b', '#0f2a3b', '#485f67', '#a2324e'),  # ref 7
    'Frost':      ('#83bfbf', '#b4d3cb', '#688180', '#688180', '#dbede3', '#3a7581'),  # ref 1
    'Camo':       ('#5d829b', '#4e6845', '#364c52', '#364c52', '#788982', '#d3d39c'),  # ref 2
    'Dune':       ('#74866b', '#b9a87b', '#485f67', '#485f67', '#d3d39c', '#a2324e'),  # ref 3
    'Tide':       ('#5daa99', '#6c78a2', '#30446c', '#30446c', '#6b8e5e', '#d5f8fc'),  # ref 4
    # --- new combinations built only from reference colours ---
    'Rust':       ('#5daa99', '#905937', '#4b2f58', '#4b2f58', '#803e31', '#c59154'),
    'Bone':       ('#7d8e61', '#d3d39c', '#997c5a', '#997c5a', '#e3e3b7', '#661e25'),
    'Glacier':    ('#6b82b4', '#8db6d1', '#30446c', '#30446c', '#cadbe1', '#d5f8fc'),
    'Spore':      ('#87789b', '#5f4754', '#2e1f36', '#4b2f58', '#87789b', '#5daa99'),
    'Crimson':    ('#87789b', '#a2324e', '#4b2f58', '#661e25', '#803e31', '#e3e3b7'),
    'Lichen':     ('#5d829b', '#849568', '#37595f', '#37595f', '#64794b', '#d3d39c'),
    'Slate':      ('#6c78a2', '#485f67', '#243039', '#0f2a3b', '#688180', '#82b7b4'),
    'Ash':        ('#6b82b4', '#788982', '#364c52', '#364c52', '#a3b7b1', '#a2324e'),
    'Deep Teal':  ('#5daa99', '#37595f', '#1b3a3a', '#0f2a3b', '#3a7581', '#e3e3b7'),
    'Mauve':      ('#6b82b4', '#87789b', '#4f335d', '#4b2f58', '#5f4754', '#e3e3b7'),
    'Pewter':     ('#87789b', '#a3b7b1', '#485f67', '#485f67', '#cbdede', '#a2324e'),
    'Abyss':      ('#596d9b', '#30446c', '#0f2a3b', '#0f2a3b', '#48557e', '#82b7b4'),
    'Sage':       ('#87789b', '#7d8e61', '#4f335d', '#4b2f58', '#849568', '#e3e3b7'),
}

COLORWAYS = {
    name: dict(FIXED, T=t, B=b, D=d, S=s, P=p, X=x)
    for name, (t, b, d, s, p, x) in _CW.items()
}
