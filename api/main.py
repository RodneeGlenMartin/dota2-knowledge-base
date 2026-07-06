"""REST API over the Dota 2 knowledge base (Valve datafeed + Liquipedia).

Run:  uvicorn api.main:app --reload
Docs: http://127.0.0.1:8000/docs
"""

import json
import pathlib

from fastapi import FastAPI, HTTPException, Query

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"

app = FastAPI(
    title="Dota 2 Knowledge Base API",
    description=(
        "Heroes and items from Valve's official dota2.com datafeed "
        "(patch-current), plus game-mechanics articles from Liquipedia "
        "(CC-BY-SA 3.0)."
    ),
    version="1.0.0",
)


def read_json(path: pathlib.Path):
    if not path.exists():
        raise HTTPException(404, f"{path.stem} not found")
    return json.loads(path.read_text(encoding="utf-8"))


def load_index(kind: str):
    return read_json(DATA / kind / "_index.json")


@app.get("/")
def root():
    return {
        "endpoints": ["/patch", "/heroes", "/heroes/{slug}", "/items",
                      "/items/{slug}", "/mechanics", "/mechanics/{slug}",
                      "/search?q="],
        "docs": "/docs",
    }


@app.get("/patch")
def current_patch():
    patches = read_json(DATA / "raw" / "valve_patches.json")
    return patches[-1]


@app.get("/heroes")
def list_heroes(
    role: str | None = Query(None, description="Filter by role, e.g. Carry"),
    attribute: str | None = Query(None, description="str, agi, int, universal"),
):
    heroes = load_index("heroes")
    if role:
        heroes = [h for h in heroes
                  if role.lower() in (r.lower() for r in h["roles"])]
    if attribute:
        heroes = [h for h in heroes
                  if h["primary_attribute"] == attribute.lower()]
    return heroes


@app.get("/heroes/{slug}")
def get_hero(slug: str):
    return read_json(DATA / "heroes" / f"{slug}.json")


@app.get("/items")
def list_items(
    neutral_tier: int | None = Query(None, ge=1, le=5),
    max_cost: int | None = Query(None, ge=0),
):
    items = load_index("items")
    if neutral_tier is not None:
        items = [i for i in items if i.get("neutral_tier") == neutral_tier]
    if max_cost is not None:
        items = [i for i in items
                 if i.get("cost") is not None and i["cost"] <= max_cost]
    return items


@app.get("/items/{slug}")
def get_item(slug: str):
    return read_json(DATA / "items" / f"{slug}.json")


@app.get("/mechanics")
def list_mechanics():
    return read_json(DATA / "mechanics" / "_index.json")


@app.get("/mechanics/{slug}")
def get_mechanic(slug: str):
    page = read_json(DATA / "mechanics" / f"{slug}.json")
    page.pop("wikitext", None)  # keep responses light; raw wikitext on disk
    return page


@app.get("/search")
def search(q: str = Query(..., min_length=2)):
    """Name search across heroes, items, and mechanics articles."""
    ql = q.lower()
    results = []
    for h in load_index("heroes"):
        if ql in h["name"].lower():
            results.append({"type": "hero", "name": h["name"],
                            "url": f"/heroes/{h['slug']}"})
    for i in load_index("items"):
        if ql in i["name"].lower():
            results.append({"type": "item", "name": i["name"],
                            "url": f"/items/{i['slug']}"})
    mech_index = DATA / "mechanics" / "_index.json"
    if mech_index.exists():
        for m in json.loads(mech_index.read_text(encoding="utf-8")):
            if ql in m["title"].lower():
                slug = m["file"].removesuffix(".json")
                results.append({"type": "mechanic", "name": m["title"],
                                "url": f"/mechanics/{slug}"})
    return results
