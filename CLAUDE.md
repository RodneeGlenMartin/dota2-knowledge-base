# Project notes for Claude

- Never add `Co-Authored-By` trailers (or any AI attribution) to git commits.
- Hero/item data source of truth is Valve's dota2.com datafeed
  (`scripts/fetch_valve.py`); third-party constants (dotaconstants, Stratz)
  lag on letter patches — do not reintroduce them as primary sources.
- `.env` holds secrets (Stratz token) and must stay gitignored.
