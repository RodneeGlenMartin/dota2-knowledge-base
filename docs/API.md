# Dota 2 Knowledge Base — Public API

A public, read-only REST API over the knowledge base, hosted on Supabase
(PostgREST). Data comes from Valve's official dota2.com datafeed
(patch-current) and Liquipedia (CC-BY-SA 3.0).

## Base URL & authentication

```
Base URL:  https://jcrjjbxfgdurusyxkbdv.supabase.co/rest/v1
API key:   sb_publishable_K7WTvmVVco1TK2hTvET33A_ChCVIWPB
```

The key is a *publishable* key — safe to embed in clients. Send it on every
request as both headers:

```
apikey: <key>
Authorization: Bearer <key>
```

The database is read-only for the public (Row Level Security allows SELECT
only).

## Quick examples

```bash
KEY=sb_publishable_K7WTvmVVco1TK2hTvET33A_ChCVIWPB
BASE=https://jcrjjbxfgdurusyxkbdv.supabase.co/rest/v1

# current patch
curl "$BASE/meta?key=eq.current_patch" -H "apikey: $KEY" -H "Authorization: Bearer $KEY"

# all heroes (name + roles)
curl "$BASE/heroes?select=name,slug,primary_attribute,roles" -H "apikey: $KEY" -H "Authorization: Bearer $KEY"

# one hero, full record (stats, abilities, talents, lore)
curl "$BASE/heroes?slug=eq.kez&select=data" -H "apikey: $KEY" -H "Authorization: Bearer $KEY"

# agility carries
curl "$BASE/heroes?primary_attribute=eq.agi&roles=cs.{Carry}&select=name" -H "apikey: $KEY" -H "Authorization: Bearer $KEY"

# items under 2000 gold, cheapest first
curl "$BASE/items?cost=lte.2000&order=cost.asc&select=name,cost" -H "apikey: $KEY" -H "Authorization: Bearer $KEY"

# tier-3 neutral items
curl "$BASE/items?neutral_tier=eq.3&select=name" -H "apikey: $KEY" -H "Authorization: Bearer $KEY"

# name search (case-insensitive)
curl "$BASE/items?name=ilike.*blade*&select=name,slug" -H "apikey: $KEY" -H "Authorization: Bearer $KEY"

# a mechanics article (without wikitext)
curl "$BASE/mechanics?slug=eq.armor&select=title,source_url,license,content" -H "apikey: $KEY" -H "Authorization: Bearer $KEY"
```

## Tables

### `heroes` (127 rows)

| Column | Type | Notes |
|---|---|---|
| `id` | int | Valve hero id |
| `slug` | text | e.g. `anti_mage`, `kez` |
| `name` | text | display name |
| `primary_attribute` | text | `str` / `agi` / `int` / `universal` |
| `attack_type` | text | `Melee` / `Ranged` |
| `roles` | text[] | e.g. `{Carry,Escape,Nuker}` |
| `data` | jsonb | full record: stats, lore, abilities (cooldowns, mana costs, per-level special values, Aghanim upgrades), talents |

### `items` (507 rows)

| Column | Type | Notes |
|---|---|---|
| `id` | int | Valve item id |
| `slug` | text | e.g. `blink_dagger` |
| `name` | text | display name |
| `cost` | int | gold cost (null for unpurchasable) |
| `neutral_tier` | int | 1-5, null for regular items |
| `data` | jsonb | full record: description, cooldowns, special values, lore |

### `mechanics` (14 rows)

| Column | Type | Notes |
|---|---|---|
| `slug` | text | e.g. `armor`, `attack_speed` |
| `title` | text | article title |
| `source_url` | text | Liquipedia page |
| `license` | text | CC-BY-SA 3.0 |
| `attribution` | text | required attribution string |
| `content` | text | plain-text article |
| `wikitext` | text | original wiki markup |

### `meta`

`key = 'current_patch'` → `{"patch_number": "7.41d", ...}` — the patch the
data was built from.

## Query syntax (PostgREST)

Filtering is done with URL operators — the most useful:

| Operator | Example |
|---|---|
| `eq.` / `neq.` | `?slug=eq.kez` |
| `lte.` / `gte.` / `lt.` / `gt.` | `?cost=lte.2000` |
| `ilike.` | `?name=ilike.*dagger*` |
| `cs.` (array contains) | `?roles=cs.{Carry,Escape}` |
| `select=` | `?select=name,cost,data->lore` |
| `order=` | `?order=cost.desc` |
| `limit=` / `offset=` | `?limit=20&offset=20` |

JSONB drilling works in `select` and filters: `data->stats->>movement_speed`,
`data->abilities` etc. Full reference:
https://postgrest.org/en/stable/references/api/tables_views.html

## Deep JSON examples

```bash
# just Kez's ability names and cooldowns
curl "$BASE/heroes?slug=eq.kez&select=data->abilities" -H "apikey: $KEY" -H "Authorization: Bearer $KEY"

# movement speed of every hero
curl "$BASE/heroes?select=name,ms:data->stats->movement_speed" -H "apikey: $KEY" -H "Authorization: Bearer $KEY"

# heroes faster than 320 ms
curl "$BASE/heroes?data->stats->movement_speed=gt.320&select=name" -H "apikey: $KEY" -H "Authorization: Bearer $KEY"
```

## Refreshing after a game patch

Maintainers (requires DB credentials in `.env`):

```bash
python scripts/fetch_valve.py     # pull latest from Valve
python scripts/build_kb.py        # rebuild data/ files
python scripts/load_supabase.py   # reload the database
```

## Attribution

- Hero/item data © Valve Corporation, via the public dota2.com datafeed.
- Mechanics articles from the [Liquipedia Dota 2 wiki](https://liquipedia.net/dota2),
  licensed CC-BY-SA 3.0. If you republish them, keep the attribution field.
