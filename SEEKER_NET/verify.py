#!/usr/bin/env python3
"""Re-draw every artwork of the collection from the layers and check it.

    python3 verify.py              # all 2,222 seekers: 13,332 uncharged pictures and 2,222 GIFs
    python3 verify.py --sample 50  # 50 seekers picked at random

Each drawing is compared with the pixel checksum of the collection's finished
file (lists/artworks.csv; the files themselves are on Arweave): the six
uncharged pictures and every frame of the activated GIF. Exits with an error
if anything differs.
"""
import argparse
import csv
import os
import random
import sys
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'engine'))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402

import animate_collection as A  # noqa: E402
import final as F  # noqa: E402
from seeker import pixel_hash  # noqa: E402


def check(row):
    t = {k: (None if row[k] == 'None' else row[k]) for k in F.KEYS}
    n = row['file_number']
    bad = []
    for s in range(1, F.STAGES + 1):
        mine = np.array(F.compose_dormant(t, s).convert('RGB'))
        if pixel_hash([mine]) != row[f'uncharged_stage_{s}_pixels_sha256']:
            bad.append(f'uncharged {s}/{n}.png')
    frames, _ = A.Seeker(t, int(row['artwork']), os.path.join(HERE, row['background_layer'])).render()
    if pixel_hash([A.rgb_frame(f) for f in frames]) != row['activated_pixels_sha256']:
        bad.append(f'activated {n}.gif')
    return int(row['artwork']), bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sample', type=int, default=0)
    ap.add_argument('--workers', type=int, default=max(1, (os.cpu_count() or 2) - 1))
    a = ap.parse_args()
    with open(os.path.join(HERE, 'lists', 'artworks.csv'), newline='') as fh:
        rows = list(csv.DictReader(fh))
    if a.sample:
        rows = random.sample(rows, a.sample)
    failed = []
    with Pool(a.workers) as pool:
        for k, (i, bad) in enumerate(pool.imap_unordered(check, rows, chunksize=4), 1):
            failed += bad
            if k % 100 == 0 or k == len(rows):
                print(f'{k} / {len(rows)} seekers, {len(failed)} pictures differ', flush=True)
    if failed:
        print('DIFFERENT:', *failed[:50], sep='\n  ')
        sys.exit(1)
    print(f'All {len(rows) * 7:,} pictures drawn from the layers match the collection, pixel for pixel.')


if __name__ == '__main__':
    main()
