# Dota 2 Knowledge Base & API

A structured knowledge base of Dota 2 heroes, items, and game mechanics with
a REST API on top.

**Data sources**

- **Valve's official dota2.com datafeed** — the JSON backend behind
  dota2.com's hero/item pages, so stats are always current with the live
  patch (verified against 7.41d).
- **[Liquipedia Dota 2 wiki](https://liquipedia.net/dota2/Mechanics)** —
  game-mechanics articles via the MediaWiki API. Content is
  [CC-BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/);
  attribution is embedded in each article file.

## Quick start

```bash
pip install -r requirements.txt

# refresh data (heroes + items from Valve, ~3 min)
python scripts/fetch_valve.py
python scripts/build_kb.py

# run the API
uvicorn api.main:app --reload
# then open http://127.0.0.1:8000/docs
```

## API endpoints

| Endpoint | Description |
|---|---|
| `GET /patch` | Current game patch |
| `GET /heroes` | Hero list; filters: `?role=Carry`, `?attribute=agi` |
| `GET /heroes/{slug}` | Full hero record (stats, abilities, talents, lore) |
| `GET /items` | Item list; filters: `?neutral_tier=3`, `?max_cost=2000` |
| `GET /items/{slug}` | Full item record |
| `GET /mechanics` | Mechanics article list |
| `GET /mechanics/{slug}` | Article text + source attribution |
| `GET /search?q=` | Name search across everything |

## Layout

```
api/main.py           FastAPI app serving the knowledge base
data/
  raw/                Valve datafeed downloads (heroes, items, patch list)
  heroes/             one JSON per hero + _index.json
  items/              one JSON per item + _index.json
  mechanics/          one JSON per Liquipedia article + _index.json
scripts/
  fetch_valve.py      download hero/item data from Valve's datafeed
  build_kb.py         assemble data/heroes and data/items from raw
  fetch_liquipedia.py download mechanics articles (batched, rate-limited)
```

## Record shapes

- `data/heroes/<slug>.json` — attributes, base stats, roles, complexity,
  lore, abilities (cooldowns, mana costs, per-level special values,
  Aghanim's Scepter/Shard upgrades), talents.
- `data/items/<slug>.json` — cost, neutral tier, description, cooldowns,
  special values, lore.
- `data/mechanics/<slug>.json` — title, source URL, license/attribution,
  wikitext, and a plain-text rendering.

## Notes

- Facets don't appear anywhere because Valve removed the Facet system in
  patch 7.41.
- Third-party constants sources (dotaconstants, Stratz) lag behind on
  letter patches, which is why this project fetches from Valve directly.
