"""Load the knowledge base into Supabase Postgres.

Creates public read-only tables (heroes, items, mechanics) served by
Supabase's auto-generated REST API (PostgREST). Row Level Security allows
anonymous SELECT only; writes require the service role.

Requires in .env (or environment):
  SUPABASE_DB_HOST, SUPABASE_DB_USER, SUPABASE_DB_PASSWORD
"""

import json
import os
import pathlib

import psycopg

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

SCHEMA = """
create table if not exists heroes (
  id integer primary key,
  slug text unique not null,
  name text not null,
  primary_attribute text,
  attack_type text,
  roles text[] not null default '{}',
  data jsonb not null
);
create table if not exists items (
  id integer primary key,
  slug text unique not null,
  name text not null,
  cost integer,
  neutral_tier integer,
  data jsonb not null
);
create table if not exists mechanics (
  slug text primary key,
  title text not null,
  source_url text,
  license text,
  attribution text,
  content text,
  wikitext text
);
create table if not exists meta (
  key text primary key,
  value jsonb not null
);

alter table heroes enable row level security;
alter table items enable row level security;
alter table mechanics enable row level security;
alter table meta enable row level security;

drop policy if exists "public read" on heroes;
drop policy if exists "public read" on items;
drop policy if exists "public read" on mechanics;
drop policy if exists "public read" on meta;
create policy "public read" on heroes for select using (true);
create policy "public read" on items for select using (true);
create policy "public read" on mechanics for select using (true);
create policy "public read" on meta for select using (true);
"""


def env(name):
    val = os.environ.get(name)
    if not val:
        for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
            if line.startswith(f"{name}="):
                val = line.split("=", 1)[1].strip()
    if not val:
        raise SystemExit(f"{name} not set")
    return val


def main():
    conn = psycopg.connect(
        host=env("SUPABASE_DB_HOST"), port=5432,
        user=env("SUPABASE_DB_USER"), password=env("SUPABASE_DB_PASSWORD"),
        dbname="postgres", connect_timeout=20,
    )
    conn.execute(SCHEMA)

    with conn.cursor() as cur:
        cur.execute("truncate heroes, items, mechanics, meta")

        for f in sorted((DATA / "heroes").glob("*.json")):
            if f.name == "_index.json":
                continue
            h = json.loads(f.read_text(encoding="utf-8"))
            cur.execute(
                "insert into heroes (id, slug, name, primary_attribute,"
                " attack_type, roles, data) values (%s,%s,%s,%s,%s,%s,%s)",
                (h["id"], h["slug"], h["name"], h["primary_attribute"],
                 h["attack_type"], h["roles"], json.dumps(h)),
            )

        for f in sorted((DATA / "items").glob("*.json")):
            if f.name == "_index.json":
                continue
            it = json.loads(f.read_text(encoding="utf-8"))
            cur.execute(
                "insert into items (id, slug, name, cost, neutral_tier, data)"
                " values (%s,%s,%s,%s,%s,%s)",
                (it["id"], it["slug"], it["name"], it["cost"],
                 it["neutral_tier"], json.dumps(it)),
            )

        for f in sorted((DATA / "mechanics").glob("*.json")):
            if f.name == "_index.json":
                continue
            m = json.loads(f.read_text(encoding="utf-8"))
            cur.execute(
                "insert into mechanics (slug, title, source_url, license,"
                " attribution, content, wikitext)"
                " values (%s,%s,%s,%s,%s,%s,%s)",
                (f.stem, m["title"], m["source_url"], m["license"],
                 m["attribution"], m.get("text"), m.get("wikitext")),
            )

        patches = json.loads(
            (DATA / "raw" / "valve_patches.json").read_text(encoding="utf-8"))
        cur.execute("insert into meta (key, value) values (%s,%s)",
                    ("current_patch", json.dumps(patches[-1])))

        cur.execute("select (select count(*) from heroes),"
                    " (select count(*) from items),"
                    " (select count(*) from mechanics)")
        print("loaded heroes/items/mechanics:", cur.fetchone())

    conn.commit()
    conn.close()


if __name__ == "__main__":
    main()
