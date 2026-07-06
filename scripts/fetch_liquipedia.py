"""Fetch Dota 2 mechanics articles from Liquipedia via the MediaWiki API.

Uses action=query with batched titles (up to 50 per request), which falls
under Liquipedia's standard rate limit (1 request / 2 s) instead of the much
stricter action=parse limit (1 / 30 s). All pages arrive in 1-2 requests.

Respects Liquipedia's API terms (https://liquipedia.net/api-terms-of-use):
- custom User-Agent with contact info
- content is CC-BY-SA 3.0; attribution stored alongside each article
"""

import json
import pathlib
import re
import time

import requests

API = "https://liquipedia.net/dota2/api.php"
HEADERS = {
    "User-Agent": "dota2-knowledge-base/0.1 (rodneeglenamerkhan@gmail.com)",
    "Accept-Encoding": "gzip",
}
RATE_SECONDS = 2.5
BATCH = 50
OUT = pathlib.Path(__file__).resolve().parent.parent / "data" / "mechanics"

# Core mechanics pages linked from https://liquipedia.net/dota2/Mechanics
PAGES = [
    "Mechanics",
    "Attack_damage",
    "Armor",
    "Magic_resistance",
    "Attributes",
    "Attack_speed",
    "Movement_speed",
    "Evasion",
    "Health_regeneration",
    "Mana_regeneration",
    "Spell_amplification",
    "Status_resistance",
    "Illusions",
    "Creep_control_techniques",
    "Denying",
    "Experience",
    "Gold",
    "Lane_creeps",
    "Neutral_creeps",
    "Roshan",
    "Runes",
    "Towers",
    "Barracks",
    "Wards",
    "Couriers",
    "Day-Night_Cycle",
    "Vision",
    "Disjoint",
    "Attack_animation",
    "Pseudo-random_distribution",
    # Patch changelogs newer than third-party constants baselines
    "Version_7.41",
    "Version_7.41b",
    "Version_7.41c",
    "Version_7.41d",
]

session = requests.Session()
session.headers.update(HEADERS)
_last_request = 0.0


def api_get(params):
    global _last_request
    wait = RATE_SECONDS - (time.monotonic() - _last_request)
    if wait > 0:
        time.sleep(wait)
    for attempt in range(5):
        r = session.get(API, params=params, timeout=60)
        _last_request = time.monotonic()
        if r.status_code == 429:
            retry_after = int(r.headers.get("Retry-After", 0) or 0)
            time.sleep(max(retry_after, 30 * (attempt + 1)))
            continue
        break
    r.raise_for_status()
    return r.json()


def wikitext_to_text(wt: str) -> str:
    """Rough plain-text rendering of wikitext for search/reading."""
    wt = re.sub(r"<!--.*?-->", "", wt, flags=re.S)
    wt = re.sub(r"<ref[^>]*/>|<ref.*?</ref>", "", wt, flags=re.S)
    wt = re.sub(r"\{\{[^{}]*\}\}", "", wt)  # simple templates
    wt = re.sub(r"\{\{[^{}]*\}\}", "", wt)  # nested leftovers, second pass
    wt = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", wt)  # links
    wt = re.sub(r"'{2,}", "", wt)  # bold/italic
    wt = re.sub(r"<[^>]+>", "", wt)  # html tags
    return re.sub(r"\n{3,}", "\n\n", wt).strip()


def slug_for(title: str) -> str:
    return title.replace(" ", "_").replace("/", "_").lower()


def fetch_batch(titles):
    data = api_get({
        "action": "query",
        "titles": "|".join(titles),
        "prop": "revisions",
        "rvprop": "content|timestamp",
        "rvslots": "main",
        "redirects": "1",
        "format": "json",
        "formatversion": "2",
    })
    pages = []
    for p in data["query"]["pages"]:
        if p.get("missing") or not p.get("revisions"):
            print(f"  MISSING: {p.get('title')}")
            continue
        rev = p["revisions"][0]
        wikitext = rev["slots"]["main"]["content"]
        pages.append({
            "title": p["title"],
            "source_url": f"https://liquipedia.net/dota2/{p['title'].replace(' ', '_')}",
            "license": "CC-BY-SA 3.0",
            "attribution": f"Content from Liquipedia Dota 2 wiki ({p['title']})",
            "revision_timestamp": rev.get("timestamp"),
            "wikitext": wikitext,
            "text": wikitext_to_text(wikitext),
        })
    return pages


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    todo = [t for t in PAGES if not (OUT / f"{slug_for(t)}.json").exists()]
    print(f"{len(PAGES) - len(todo)} cached, fetching {len(todo)}")

    for i in range(0, len(todo), BATCH):
        for page in fetch_batch(todo[i:i + BATCH]):
            path = OUT / f"{slug_for(page['title'])}.json"
            path.write_text(json.dumps(page, indent=2, ensure_ascii=False),
                            encoding="utf-8")
            print(f"saved {path.name}")

    index = []
    for t in PAGES:
        path = OUT / f"{slug_for(t)}.json"
        if path.exists():
            page = json.loads(path.read_text(encoding="utf-8"))
            index.append({"title": page["title"], "file": path.name,
                          "url": page["source_url"]})
    (OUT / "_index.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"done: {len(index)} articles")


if __name__ == "__main__":
    main()
