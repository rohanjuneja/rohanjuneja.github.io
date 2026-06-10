#!/usr/bin/env python3
"""
build_service.py — auto-fill official URLs for venues in data/service.yml.

For each venue written as a map ({name: ..., year: ...}) that has no `url`, this
resolves the venue's official website and writes it back into service.yml:
  1. a curated map of well-known venues (matched by the acronym in parentheses,
     e.g. "(MICRO)"), then
  2. Wikidata's "official website" (P856) as a best-effort fallback (mostly
     useful for journals).
If nothing confident is found, the venue is left as-is (add the url by hand).

Design notes
------------
- Only MAP venues missing `url` are touched. Plain-string venues and venues that
  already have a `url` are never modified (your manual links always win).
- Comments and formatting in service.yml are preserved (ruamel round-trip).
- Idempotent: once a url is filled it is skipped, so re-runs make no changes.

Runs automatically in CI; or: pip install -r scripts/requirements.txt &&
python scripts/build_service.py   (flags: --no-fetch, --dry-run)
"""

import argparse
import difflib
import os
import re
import sys

import ruamel.yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVICE = os.path.join(ROOT, "data", "service.yml")

# Curated official sites for common venues, keyed by lowercase acronym. These are
# stable series homepages (a conference's per-year site changes, so we link the
# series). Only include venues we're confident about.
VENUE_URLS = {
    "micro": "https://www.microarch.org/",
    "isca": "https://iscaconf.org/",
    "asplos": "https://www.asplos-conference.org/",
    "hpca": "https://hpca-conf.org/",
    "pact": "https://pactconf.org/",
    "dac": "https://www.dac.com/",
    "iccad": "https://www.iccad.com/",
    "date": "https://www.date-conference.com/",
    "asp-dac": "https://www.aspdac.com/",
    "aspdac": "https://www.aspdac.com/",
    "isqed": "https://www.isqed.org/",
    "hotchips": "https://hotchips.org/",
    "isocc": "https://www.isocc.org/",
    "islped": "https://www.islped.org/",
    "trets": "https://dl.acm.org/journal/trets",
}

UA = {"User-Agent": "rohanjuneja.github.io service-links (mailto:juneja@u.nus.edu)"}


def acronyms_in(name):
    """Acronyms to try: parenthetical tokens, plus a leading all-caps token."""
    cands = []
    for tok in re.findall(r"\(([^)]+)\)", name):
        cands.append(tok.strip())
    lead = name.strip().split()
    if lead and re.fullmatch(r"[A-Z][A-Z0-9\-]{1,}", lead[0]):
        cands.append(lead[0])
    out = []
    for c in cands:
        key = re.sub(r"[^a-z0-9\-]", "", c.lower())
        if key and key not in out:
            out.append(key)
    return out


def clean_name(name):
    name = re.sub(r"\([^)]*\)", "", name)   # drop "(MICRO)"
    name = re.sub(r",\s*(?:19|20)\d{2}\s*$", "", name)  # drop trailing ", 2025"
    # Keep any "IEEE"/"ACM" prefix — Wikidata journal labels include it, which
    # improves matching (e.g. "IEEE Transactions on Computer-Aided Design ...").
    return re.sub(r"\s+", " ", name).strip()


def wikidata_official_site(name, session):
    """Best-effort: return the official website (P856) of the best-matching entity."""
    q = clean_name(name)
    try:
        s = session.get(
            "https://www.wikidata.org/w/api.php",
            params={"action": "wbsearchentities", "search": q, "language": "en",
                    "format": "json", "limit": 5},
            headers=UA, timeout=20,
        ).json()
    except Exception as e:
        print("    wikidata search error: %s" % e)
        return None
    for cand in s.get("search", []):
        label = cand.get("label", "")
        if difflib.SequenceMatcher(None, q.lower(), label.lower()).ratio() < 0.6:
            continue
        try:
            ent = session.get(
                "https://www.wikidata.org/w/api.php",
                params={"action": "wbgetentities", "ids": cand["id"],
                        "props": "claims", "format": "json"},
                headers=UA, timeout=20,
            ).json()
            claims = ent["entities"][cand["id"]].get("claims", {})
            p856 = claims.get("P856")
            if p856:
                return p856[0]["mainsnak"]["datavalue"]["value"]
        except Exception:
            continue
    return None


def resolve_url(name, no_fetch, session):
    for acr in acronyms_in(name):
        if acr in VENUE_URLS:
            return VENUE_URLS[acr], "curated"
    if not no_fetch:
        url = wikidata_official_site(name, session)
        if url:
            return url, "wikidata"
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-fetch", action="store_true", help="skip Wikidata lookup")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not os.path.exists(SERVICE):
        print("No %s — nothing to do." % SERVICE)
        return

    yaml = ruamel.yaml.YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096  # never line-wrap (would split values mid-token)
    yaml.indent(mapping=2, sequence=4, offset=2)  # keep the "  - role:" style
    with open(SERVICE) as f:
        data = yaml.load(f)

    groups = (data or {}).get("service") or []
    session = None
    if not args.no_fetch:
        import requests
        session = requests.Session()

    changed = 0
    print("\n=== Service link resolution ===")
    for g in groups:
        for i, v in enumerate(g.get("venues", []) or []):
            # Only operate on map venues that lack a url.
            if not isinstance(v, dict):
                print("  skip (free-text): %s" % v)
                continue
            if v.get("url"):
                print("  keep  (has url): %s" % v.get("name"))
                continue
            name = v.get("name", "")
            url, src = resolve_url(name, args.no_fetch, session)
            if url:
                v["url"] = url
                changed += 1
                print("  set   [%s]: %s -> %s" % (src, name, url))
            else:
                print("  none  (add manually): %s" % name)

    if changed and not args.dry_run:
        with open(SERVICE, "w") as f:
            yaml.dump(data, f)
        print("\nUpdated %s (%d url(s) filled)." % (SERVICE, changed))
    elif args.dry_run:
        print("\n[dry-run] %d url(s) would be filled." % changed)
    else:
        print("\nNo changes — all resolvable venues already linked.")


if __name__ == "__main__":
    main()
