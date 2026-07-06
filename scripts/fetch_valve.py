"""Fetch patch-current hero/item data from Valve's official dota2.com datafeed.

This is the same JSON backend that powers dota2.com's hero/item pages, so it
is always current with the live patch (verified: reflects 7.41d changes that
dotaconstants and Stratz still lack).

Outputs:
  data/raw/valve_heroes.json  - full herodata for every hero
  data/raw/valve_items.json   - full itemdata for every item
  data/raw/valve_patches.json - patch list with timestamps
"""

import json
import pathlib
import time

import requests

BASE = "https://www.dota2.com/datafeed"
OUT = pathlib.Path(__file__).resolve().parent.parent / "data" / "raw"
DELAY = 0.25  # be polite


def get(session, path, **params):
    params["language"] = "english"
    for attempt in range(5):
        r = session.get(f"{BASE}/{path}", params=params, timeout=60)
        if r.status_code == 429:
            time.sleep(5 * (attempt + 1))
            continue
        break
    r.raise_for_status()
    return r.json()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    s = requests.Session()

    patches = get(s, "patchnoteslist")["patches"]
    (OUT / "valve_patches.json").write_text(
        json.dumps(patches, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"current patch: {patches[-1]['patch_number']}")

    hero_ids = [h["id"] for h in get(s, "herolist")["result"]["data"]["heroes"]]
    heroes = []
    for i, hid in enumerate(hero_ids, 1):
        heroes.append(get(s, "herodata", hero_id=hid)["result"]["data"]["heroes"][0])
        if i % 20 == 0:
            print(f"heroes {i}/{len(hero_ids)}")
        time.sleep(DELAY)
    (OUT / "valve_heroes.json").write_text(
        json.dumps(heroes, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"heroes: {len(heroes)}")

    item_ids = [i["id"] for i in get(s, "itemlist")["result"]["data"]["itemabilities"]]
    items = []
    for i, iid in enumerate(item_ids, 1):
        data = get(s, "itemdata", item_id=iid)["result"]["data"]["items"]
        if data:
            items.append(data[0])
        if i % 100 == 0:
            print(f"items {i}/{len(item_ids)}")
        time.sleep(DELAY)
    (OUT / "valve_items.json").write_text(
        json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"items: {len(items)}")


if __name__ == "__main__":
    main()
