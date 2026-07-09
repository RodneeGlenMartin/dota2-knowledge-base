# Dota 2 Itemization Guide app

A self-contained web app covering all 127 heroes.

## Run it

Open `app/index.html` directly in a browser (no server needed — data is
bundled in `app/data.js`), or serve the folder:

```
python -m http.server -d app
```

## Features

- **Hero Guides** — browse/search all heroes, filter by attribute or
  position. Each hero page has per-position (pos 1–5) builds: starting,
  early game, core (in order), and situational items, plus a
  "How to counter this hero" section driven by its threat tags.
- **Draft & Counter Picker** — pick your hero and role, add up to five
  enemy heroes, and get your build with counter items merged in, ranked by
  how many enemy threats each item answers (with per-enemy reasons).
  Support roles (4/5) get support-appropriate counter items.

## Regenerating the data

Builds, positions, threat tags, and counter rules live in
`scripts/build_itemization.py` (curated layer) combined with the Valve
datafeed KB in `data/heroes` and `data/items`. Rebuild after a patch:

```
python scripts/fetch_valve.py      # refresh KB (existing workflow)
python scripts/build_itemization.py
```

This regenerates `data/app/itemization.json` and `app/data.js`. The script
validates every referenced item slug against `data/items/_index.json` and
aborts on unknown slugs (e.g. renamed items after a patch).
