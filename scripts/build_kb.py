"""Assemble the knowledge base from Valve datafeed data (patch-current).

Primary source: data/raw/valve_heroes.json / valve_items.json fetched by
fetch_valve.py from dota2.com's official datafeed. dotaconstants raw files
remain in data/raw/ as a secondary reference.

Outputs:
  data/heroes/<slug>.json  - stats, roles, lore, abilities, talents, facets
  data/heroes/_index.json
  data/items/<slug>.json   - cost, stats, abilities text, components, lore
  data/items/_index.json
"""

import json
import pathlib
import re

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"
RAW = DATA / "raw"

# Order of Valve's role_levels array (same convention OpenDota uses)
ROLE_NAMES = ["Carry", "Support", "Nuker", "Disabler", "Jungler",
              "Durable", "Escape", "Pusher", "Initiator"]

ATTR_NAMES = {0: "str", 1: "agi", 2: "int", 3: "universal"}


def load(name):
    return json.loads((RAW / name).read_text(encoding="utf-8"))


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def clean_ability(a):
    return {
        "key": a.get("name"),
        "name": a.get("name_loc"),
        "description": a.get("desc_loc"),
        "max_level": a.get("max_level"),
        "cooldowns": a.get("cooldowns"),
        "mana_costs": a.get("mana_costs"),
        "health_costs": a.get("health_costs"),
        "cast_ranges": a.get("cast_ranges"),
        "cast_points": a.get("cast_points"),
        "durations": a.get("durations"),
        "damages": a.get("damages"),
        "special_values": [
            {
                "key": sv.get("name"),
                "heading": sv.get("heading_loc"),
                "values": sv.get("values_float") or sv.get("values_int"),
            }
            for sv in a.get("special_values", [])
            if sv.get("name")
        ],
        "scepter_upgrade": a.get("scepter_loc") or None,
        "shard_upgrade": a.get("shard_loc") or None,
        "notes": a.get("notes_loc") or None,
        "lore": a.get("lore_loc") or None,
    }


def build_heroes():
    heroes = load("valve_heroes.json")
    out_dir = DATA / "heroes"
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.json"):
        old.unlink()
    index = []

    for h in heroes:
        slug = slugify(h["name_loc"])
        roles = [ROLE_NAMES[i] for i, lv in enumerate(h.get("role_levels", []))
                 if i < len(ROLE_NAMES) and lv > 0]
        record = {
            "id": h["id"],
            "name": h["name_loc"],
            "slug": slug,
            "npc_name": h["name"],
            "primary_attribute": ATTR_NAMES.get(h.get("primary_attr"),
                                                h.get("primary_attr")),
            "attack_type": "Melee" if h.get("attack_capability") == 1 else "Ranged",
            "complexity": h.get("complexity"),
            "roles": roles,
            "stats": {
                "base_str": h.get("str_base"), "str_gain": h.get("str_gain"),
                "base_agi": h.get("agi_base"), "agi_gain": h.get("agi_gain"),
                "base_int": h.get("int_base"), "int_gain": h.get("int_gain"),
                "damage_min": h.get("damage_min"), "damage_max": h.get("damage_max"),
                "attack_rate": h.get("attack_rate"),
                "attack_range": h.get("attack_range"),
                "projectile_speed": h.get("projectile_speed"),
                "armor": h.get("armor"),
                "magic_resistance": h.get("magic_resistance"),
                "movement_speed": h.get("movement_speed"),
                "turn_rate": h.get("turn_rate"),
                "sight_range_day": h.get("sight_range_day"),
                "sight_range_night": h.get("sight_range_night"),
                "max_health": h.get("max_health"),
                "health_regen": h.get("health_regen"),
                "max_mana": h.get("max_mana"),
                "mana_regen": h.get("mana_regen"),
            },
            "lore": h.get("bio_loc"),
            "hype": h.get("hype_loc"),
            "abilities": [clean_ability(a) for a in h.get("abilities", [])],
            "talents": [
                {"slot": t.get("slot"), "name": t.get("name_loc")}
                for t in h.get("talents", [])
            ],
            # Facets were removed from the game in patch 7.41
            "sources": ["Valve dota2.com datafeed (official, patch-current)"],
        }
        (out_dir / f"{slug}.json").write_text(
            json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
        index.append({
            "id": h["id"], "name": h["name_loc"], "slug": slug,
            "primary_attribute": record["primary_attribute"],
            "attack_type": record["attack_type"], "roles": roles,
        })

    index.sort(key=lambda x: x["name"])
    (out_dir / "_index.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"heroes: {len(index)}")


def build_items():
    items = load("valve_items.json")
    out_dir = DATA / "items"
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.json"):
        old.unlink()
    index = []
    seen = set()

    for it in items:
        if not it.get("name_loc"):
            continue
        slug = slugify(it["name_loc"])
        if slug in seen:  # recipes etc. can duplicate display names
            slug = f"{slug}_{it['id']}"
        seen.add(slug)
        gold = it.get("gold_costs") or []
        record = {
            "id": it["id"],
            "name": it["name_loc"],
            "slug": slug,
            "internal_key": it.get("name"),
            "cost": it.get("item_cost") or (gold[0] if gold else None),
            "neutral_tier": (it.get("neutral_item_tier")
                             if it.get("neutral_item_tier", -1) >= 0 else None),
            "description": it.get("desc_loc"),
            "notes": it.get("notes_loc") or None,
            "cooldowns": it.get("cooldowns"),
            "mana_costs": it.get("mana_costs"),
            "cast_ranges": it.get("cast_ranges"),
            "special_values": [
                {
                    "key": sv.get("name"),
                    "heading": sv.get("heading_loc"),
                    "values": sv.get("values_float") or sv.get("values_int"),
                }
                for sv in it.get("special_values", [])
                if sv.get("name")
            ],
            "lore": it.get("lore_loc") or None,
            "sources": ["Valve dota2.com datafeed (official, patch-current)"],
        }
        (out_dir / f"{slug}.json").write_text(
            json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
        index.append({
            "id": it["id"], "name": it["name_loc"], "slug": slug,
            "cost": record["cost"], "neutral_tier": record["neutral_tier"],
        })

    index.sort(key=lambda x: x["name"])
    (out_dir / "_index.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"items: {len(index)}")


if __name__ == "__main__":
    build_heroes()
    build_items()
