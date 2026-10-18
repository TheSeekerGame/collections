# collections

The two collections of [The Seeker](https://github.com/TheSeekerGame/the-seeker), packaged so that any game can use
them: every art layer, the exact rules that put a picture together, and how to read each one's live state from
public APIs.

| Folder | Collection | Chain | What changes on-chain |
|---|---|---|---|
| [`guardians/`](guardians/) | Planetary Guardians: 333 inscriptions | Bitcoin (ordinals) | a Guardian's look, which its holder sets through its padding |
| [`SEEKER_NET/`](SEEKER_NET/) | SEEKER NET: 2,222 tokens | Robinhood Chain | each seeker's charge, status (Dormant or Activated), Discharge and Uplink |

Both appear in The Seeker's lore; [the open brand](https://github.com/TheSeekerGame/the-seeker/blob/main/docs/design/open-brand.md)
describes their role in the game.

## One source of truth, no server

The chain is the only source of truth. A game reads it through public APIs, with no account or server of ours in
between, so when a holder changes a Guardian's look or a seeker's charge moves, every game shows the change,
single-player games included. Each folder's README has a **Live data for games** section with the endpoints,
example requests, how to turn the answers into the current picture, polling and caching advice, and rate limits.
Each folder also has a `live.py` that does it:

```sh
cd guardians
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
python live.py --id 0000038e69f964da83318a45cd892abffbc63f73e0d08436d2ade37f5d8b3000i0
```

```sh
cd SEEKER_NET
python3 live.py 1895
```

Everything that never changes, the art layers above all, is in these folders, so a game only asks the chain for
the few values that move.

## License

Everything here, code, art layers and data alike, is licensed under either of [MIT](LICENSE-MIT) or
[Apache-2.0](LICENSE-APACHE), at your option, like The Seeker's code. See [LICENSE.md](LICENSE.md).
