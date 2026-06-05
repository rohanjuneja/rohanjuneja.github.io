#!/usr/bin/env python3
"""
build_publications.py — regenerate data/publications.yml from files/resume.pdf.

What it does
------------
1. Parses the "Publication Record" of files/resume.pdf (Conferences / Journals /
   Chip Tapeouts / Patents) into structured entries: title, venue, year, status
   tags, authors, equal-contribution.
2. Scaffolds a per-paper folder publications/<slug>/ with a links.yml. You drop
   slides.pdf / paper.pdf into that folder and they get linked automatically.
3. Auto-fetches each published paper's DOI from Crossref (fallback DBLP) and
   caches it in the folder's links.yml so builds are idempotent and you can pin
   or correct it.
4. Applies publications/overrides.yml for any manual corrections.
5. Writes data/publications.yml (grouped by category, newest-first) and prints a
   manifest. On a parse failure it exits non-zero WITHOUT writing, so a bad parse
   never overwrites good data.

You should not normally run this by hand — the GitHub Action does it on push.
But you can: `pip install -r scripts/requirements.txt && python scripts/build_publications.py`

Flags: --no-fetch (skip network DOI lookup), --dry-run (don't write files).
"""

import argparse
import difflib
import os
import re
import sys
import time

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESUME = os.path.join(ROOT, "files", "resume.pdf")
PUBS_DIR = os.path.join(ROOT, "publications")
OUT_YAML = os.path.join(ROOT, "data", "publications.yml")
OVERRIDES = os.path.join(PUBS_DIR, "overrides.yml")

SECTIONS = ["Conferences", "Journals", "Chip Tapeouts", "Patents"]
# Where parsing stops (first top-level heading after the publication record).
END_MARKERS = ["Teaching Experience", "Awards", "Skills", "Service", "References"]

# Acronym -> full venue name. Unknown venues fall back to just the acronym.
VENUE_NAMES = {
    "MICRO": "International Symposium on Microarchitecture",
    "ICCAD": "International Conference on Computer-Aided Design",
    "AAAI": "AAAI Conference on Artificial Intelligence",
    "ASPLOS": "International Conference on Architectural Support for Programming Languages and Operating Systems",
    "PACT": "International Conference on Parallel Architectures and Compilation Techniques",
    "DATE": "Design, Automation and Test in Europe Conference",
    "DAC": "Design Automation Conference",
    "ASP-DAC": "Asia and South Pacific Design Automation Conference",
    "ISQED": "International Symposium on Quality Electronic Design",
    "TRETS": "ACM Transactions on Reconfigurable Technology and Systems",
    "TVLSI": "IEEE Transactions on Very Large Scale Integration Systems",
    "HotChips": "Hot Chips Symposium",
    "ISOCC": "International System-on-Chip Conference",
    "TBioCAS": "IEEE Transactions on Biomedical Circuits and Systems",
}

NAME = "Rohan Juneja"
NAME_HTML = "<u><strong>Rohan Juneja</strong></u>"
STAR = "∗"  # ∗ used for equal contribution in the resume


# --------------------------------------------------------------------------- #
# PDF extraction + parsing
# --------------------------------------------------------------------------- #
def extract_lines():
    import pdfplumber

    lines = []
    with pdfplumber.open(RESUME) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for raw in text.split("\n"):
                line = raw.strip()
                if line:
                    lines.append(line)
    return lines


def parse_resume(lines):
    """Return a list of entry dicts in resume order."""
    # Narrow to the publication record region.
    try:
        start = next(i for i, l in enumerate(lines) if l.startswith("Publication Record"))
    except StopIteration:
        raise SystemExit("ERROR: 'Publication Record' heading not found in resume.")
    region = []
    for l in lines[start + 1 :]:
        if any(l.startswith(m) for m in END_MARKERS):
            break
        region.append(l)

    entries = []
    section = None
    cur = None  # list of lines for the current entry being accumulated

    def flush():
        nonlocal cur
        if cur and section:
            entries.append(build_entry(section, cur))
        cur = None

    for l in region:
        if l in SECTIONS:
            flush()
            section = l
            continue
        if re.match(r"^\d+\.\s", l):  # new numbered entry
            flush()
            cur = [re.sub(r"^\d+\.\s+", "", l)]
        elif cur is not None:
            cur.append(l)
    flush()
    return entries


def build_entry(section, body_lines):
    """body_lines: title/venue line(s) + author line(s) (+ footnote) for one paper."""
    # Equal-contribution footnote (e.g. "∗Equalcontribution").
    equal = False
    kept = []
    for l in body_lines:
        if l.startswith(STAR) and "qual" in l.lower():  # ∗Equal contribution
            equal = True
            continue
        kept.append(l)

    # Author line = first line containing the owner's name; everything before is
    # title/venue, that line + following lines are authors.
    author_idx = next((i for i, l in enumerate(kept) if NAME in l), None)
    if author_idx is None:
        raise SystemExit("ERROR: could not find author line (no '%s') in entry: %r" % (NAME, kept))

    title_venue = " ".join(kept[:author_idx]).strip()
    authors_raw = " ".join(kept[author_idx:]).strip()

    title, venue, year, tags = split_title_venue(section, title_venue)
    return {
        "section": section,
        "title": title,
        "venue": venue,
        "year": year,
        "tags": tags,
        "authors_raw": authors_raw,
        "equal_contribution": equal,
    }


def split_title_venue(section, s):
    """Split 'Title .... VENUE YEAR [status]' into (title, venue, year, tags)."""
    tags = []
    # Pull any trailing/bracketed status tags first (may be anywhere near the end).
    for m in re.findall(r"\[([^\]]+)\]", s):
        tags.append(m.strip())
    s_clean = re.sub(r"\s*\[[^\]]+\]\s*", " ", s).strip()

    if section == "Patents":
        # "Title ... Patent <number>, <year>"
        m = re.search(r"\bPatent\s+([0-9A-Za-z]+),?\s*((?:19|20)\d{2})\s*$", s_clean)
        if m:
            title = s_clean[: m.start()].strip()
            return title, "Patent", int(m.group(2)), tags
        return s_clean, "Patent", None, tags

    # Last "<venue-token> <year>" at the end of the string.
    m = re.search(r"(\S+)\s+((?:19|20)\d{2})\s*$", s_clean)
    if not m:
        # No detectable venue/year — leave whole string as title.
        return s_clean, None, None, tags
    venue = m.group(1)
    year = int(m.group(2))
    title = s_clean[: m.start()].strip()
    return title, venue, year, tags


# --------------------------------------------------------------------------- #
# Slug + HTML helpers
# --------------------------------------------------------------------------- #
def slugify(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text


def make_slug(title, used):
    # Acronym papers ("NEXUS: ...") get a short slug from the prefix before ':'.
    prefix = title.split(":")[0].strip() if ":" in title else title
    words = slugify(prefix).split("-")
    if len(words) > 5:
        words = slugify(title).split("-")[:5]
    base = "-".join([w for w in words if w]) or "paper"
    slug, n = base, 2
    while slug in used:
        slug = "%s-%d" % (base, n)
        n += 1
    used.add(slug)
    return slug


def esc(s):
    return s.replace("&", "&amp;")


def format_authors(authors_raw):
    s = esc(authors_raw)
    s = s.replace(NAME, NAME_HTML)
    s = s.replace(STAR, "<sup>*</sup>")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def format_venue(venue, year, section):
    if not venue:
        return None
    if venue == "Patent":
        return "Patent" + (" %d" % year if year else "")
    full = VENUE_NAMES.get(venue)
    if full:
        return "In %s (<strong>%s</strong>) %d" % (full, venue, year)
    return "In <strong>%s</strong> %d" % (venue, year)


# --------------------------------------------------------------------------- #
# Per-paper folder: links.yml + asset detection + DOI fetch
# --------------------------------------------------------------------------- #
LINKS_TEMPLATE = (
    "# Links for this paper. 'doi' is auto-fetched; edit any field to override.\n"
    "# Drop slides.pdf or paper.pdf into this folder and they link automatically.\n"
    "# Set doi to '' to mean 'no DOI' (e.g. under review) and stop auto-fetching.\n"
)


def load_links(slug):
    path = os.path.join(PUBS_DIR, slug, "links.yml")
    if os.path.exists(path):
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return data if isinstance(data, dict) else {}
    return {}


def save_links(slug, data, dry_run):
    if dry_run:
        return
    folder = os.path.join(PUBS_DIR, slug)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "links.yml")
    with open(path, "w") as f:
        f.write(LINKS_TEMPLATE)
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)


def detect_assets(slug):
    folder = os.path.join(PUBS_DIR, slug)
    found = {}
    for name, key in (("paper.pdf", "paper"), ("slides.pdf", "slides"), ("slides.pptx", "slides_pptx")):
        if os.path.exists(os.path.join(folder, name)):
            found[key] = "/publications/%s/%s" % (slug, name)
    return found


def _lead_token(t):
    m = re.match(r"^([A-Za-z0-9]+)", t.strip())
    return m.group(1).lower() if m else ""


def crossref_doi(title, year, session):
    """Best-effort DOI lookup. Accepts a candidate when the title closely matches,
    OR when the owner is a listed author and the year lines up (which safely covers
    near-miss titles like Nexus and acronym-only registrations like 'REACT')."""
    try:
        r = session.get(
            "https://api.crossref.org/works",
            params={"query.bibliographic": title, "rows": 8},
            headers={"User-Agent": "rohanjuneja.github.io build (mailto:juneja@u.nus.edu)"},
            timeout=20,
        )
        r.raise_for_status()
        items = r.json().get("message", {}).get("items", [])
    except Exception as e:
        print("    crossref error: %s" % e)
        return "__ERROR__", 0.0  # transient — caller won't cache a false 'none'

    best, best_score, best_ratio = None, -1.0, 0.0
    for it in items:
        cand = (it.get("title") or [""])[0]
        if not cand:
            continue
        ratio = difflib.SequenceMatcher(None, title.lower(), cand.lower()).ratio()
        iyear = None
        for k in ("published-print", "published-online", "issued"):
            parts = it.get(k, {}).get("date-parts", [[None]])
            if parts and parts[0] and parts[0][0]:
                iyear = parts[0][0]
                break
        year_ok = not (year and iyear) or abs(int(iyear) - int(year)) <= 1
        if not year_ok:
            continue
        has_owner = any("juneja" in (a.get("family", "").lower()) for a in it.get("author", []))
        acronym_share = _lead_token(title) and _lead_token(title) == _lead_token(cand)
        # Strong title match, or owner-confirmed (loose title) or owner+shared acronym.
        accept = ratio >= 0.82 or (has_owner and ratio >= 0.5) or (has_owner and acronym_share)
        # Rank owner-confirmed candidates above non-owner ones, then by title ratio.
        score = ratio + (0.5 if has_owner else 0.0)
        if accept and score > best_score:
            best, best_score, best_ratio = it.get("DOI"), score, ratio
    # Return the DOI plus the title-similarity (used to break duplicate-DOI ties).
    return best, best_ratio


def doi_publisher_label(doi):
    if doi.startswith("10.1109"):
        return "IEEE"
    if doi.startswith("10.1145"):
        return "ACM"
    return "DOI"


def resolve_links(slug, entry, no_fetch, session, dry_run):
    """Read/refresh links.yml, run DOI fetch if needed, return ordered link list."""
    links = load_links(slug)
    is_published = not any("review" in t.lower() for t in entry["tags"]) and entry["year"] is not None
    changed = False

    match_ratio = 1.0  # cached/pinned DOIs are trusted (used for dedup tie-breaks)
    if "doi" not in links:
        if no_fetch:
            # Didn't actually look — leave the key absent so a later fetch run
            # will try, rather than caching a false "none found".
            pass
        elif is_published and entry["section"] != "Patents":
            print("    fetching DOI for %r ..." % entry["title"][:60])
            doi, match_ratio = crossref_doi(entry["title"], entry["year"], session)
            time.sleep(0.5)  # be polite to Crossref
            if doi == "__ERROR__":
                # Network/Crossref error — leave 'doi' absent so the next run retries
                # rather than caching a false "no DOI".
                doi, match_ratio = "", 0.0
            else:
                links["doi"] = doi or ""
                changed = True
        else:
            # Under review / patent: no DOI expected — cache '' to avoid retrying.
            links["doi"] = ""
            changed = True
    for k in ("arxiv", "code", "video"):
        if k not in links:
            links[k] = ""
            changed = True
    if changed:
        save_links(slug, links, dry_run)

    assets = detect_assets(slug)
    out = []
    doi = (links.get("doi") or "").strip()
    if doi:
        out.append({"label": doi_publisher_label(doi), "url": "https://doi.org/%s" % doi})
    if assets.get("paper"):
        out.append({"label": "PDF", "url": assets["paper"]})
    if (links.get("arxiv") or "").strip():
        out.append({"label": "arXiv", "url": "https://arxiv.org/abs/%s" % links["arxiv"].strip()})
    if (links.get("code") or "").strip():
        out.append({"label": "CODE", "url": links["code"].strip()})
    if assets.get("slides"):
        out.append({"label": "SLIDES", "url": assets["slides"]})
    elif assets.get("slides_pptx"):
        out.append({"label": "SLIDES", "url": assets["slides_pptx"]})
    if (links.get("video") or "").strip():
        out.append({"label": "VIDEO", "url": links["video"].strip()})
    return out, (links.get("doi") or "").strip(), match_ratio


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-fetch", action="store_true", help="skip web DOI lookup")
    ap.add_argument("--dry-run", action="store_true", help="don't write any files")
    args = ap.parse_args()

    lines = extract_lines()
    parsed = parse_resume(lines)

    # Fail-safe: a healthy resume has well over a dozen publications.
    if len(parsed) < 10:
        raise SystemExit("ERROR: parsed only %d entries — refusing to overwrite. "
                         "Check resume layout / parser." % len(parsed))

    overrides = {}
    if os.path.exists(OVERRIDES):
        with open(OVERRIDES) as f:
            overrides = yaml.safe_load(f) or {}

    session = None
    if not args.no_fetch:
        import requests
        session = requests.Session()

    used_slugs = set()
    by_section = {s: [] for s in SECTIONS}
    manifest = []

    for e in parsed:
        slug = make_slug(e["title"], used_slugs)
        ov = overrides.get(slug, {}) if isinstance(overrides, dict) else {}
        if ov.get("exclude"):
            manifest.append((slug, e, "excluded", ""))
            continue
        # Field overrides (title/venue/year/tags/authors_raw/section).
        for k in ("title", "venue", "year", "tags", "authors_raw", "section"):
            if k in ov:
                e[k] = ov[k]

        links, doi, ratio = resolve_links(slug, e, args.no_fetch, session, args.dry_run)

        entry = {
            "slug": slug,
            "badge": e["venue"] or "",
            "year": e["year"],
            "title": e["title"],
            "authors_html": format_authors(e["authors_raw"]),
        }
        venue_html = format_venue(e["venue"], e["year"], e["section"])
        if venue_html:
            entry["venue_html"] = venue_html
        if e["tags"]:
            entry["tags"] = e["tags"]
        if e["equal_contribution"]:
            entry["equal_contribution"] = True
        if links:
            entry["links"] = links

        by_section[e["section"]].append(entry)
        entry["_doi"] = doi
        entry["_ratio"] = ratio
        manifest.append((slug, e, "ok", doi))

    # Dedup: a DOI identifies exactly one paper. If two entries resolved to the
    # same DOI (near-identical titles by the same author), keep it for the best
    # title match and clear it from the others — so e.g. an SRC abstract can't
    # inherit the full paper's DOI.
    all_entries = [en for items in by_section.values() for en in items]
    by_doi = {}
    for en in all_entries:
        if en.get("_doi"):
            by_doi.setdefault(en["_doi"], []).append(en)
    for doi, ents in by_doi.items():
        if len(ents) < 2:
            continue
        ents.sort(key=lambda x: x.get("_ratio", 0.0), reverse=True)
        winner = ents[0]
        for loser in ents[1:]:
            print("  ! duplicate DOI %s: keeping %r, clearing %r"
                  % (doi, winner["slug"], loser["slug"]))
            loser["links"] = [l for l in loser.get("links", [])
                              if not l["url"].endswith(doi)]
            if not loser["links"]:
                loser.pop("links", None)
            # Persist '' so future runs don't re-fetch the same wrong DOI.
            ln = load_links(loser["slug"])
            ln["doi"] = ""
            save_links(loser["slug"], ln, args.dry_run)
    for en in all_entries:
        en.pop("_doi", None)
        en.pop("_ratio", None)

    # Build sections (only non-empty), newest-first within each.
    sections = []
    for s in SECTIONS:
        items = by_section[s]
        if not items:
            continue
        items.sort(key=lambda x: (x["year"] or 0), reverse=True)
        sections.append({"heading": s, "entries": items})

    out = {"sections": sections}

    header = (
        "# =============================================================================\n"
        "# AUTO-GENERATED by scripts/build_publications.py from files/resume.pdf.\n"
        "# DO NOT EDIT BY HAND. To change publications:\n"
        "#   * add/edit a paper        -> edit files/resume.pdf\n"
        "#   * add slides / local PDF  -> drop slides.pdf / paper.pdf in publications/<slug>/\n"
        "#   * fix a link or DOI       -> edit publications/<slug>/links.yml\n"
        "#   * fix a misparse          -> edit publications/overrides.yml\n"
        "# The GitHub Action regenerates this file automatically on push.\n"
        "# =============================================================================\n"
    )

    # ---- manifest -----------------------------------------------------------
    print("\n=== Publications manifest (%d papers) ===" % sum(len(s["entries"]) for s in sections))
    for slug, e, status, doi in manifest:
        tagstr = (" [%s]" % "; ".join(e["tags"])) if e["tags"] else ""
        assets = detect_assets(slug)
        astr = ",".join(sorted(assets.keys())) or "-"
        final_doi = (load_links(slug).get("doi") or "").strip()  # post-dedup state
        print("  %-34s %-8s %-5s %-9s doi=%-1s assets=%s%s"
              % (slug, e.get("venue") or "?", e.get("year") or "?", e["section"][:9],
                 "Y" if final_doi else "n", astr, tagstr))
    counts = {s["heading"]: len(s["entries"]) for s in sections}
    print("  ---- counts:", counts)

    if args.dry_run:
        print("\n[dry-run] not writing %s" % OUT_YAML)
        return

    with open(OUT_YAML, "w") as f:
        f.write(header)
        yaml.safe_dump(out, f, allow_unicode=True, sort_keys=False, default_flow_style=False, width=1000)
    print("\nWrote %s" % OUT_YAML)


if __name__ == "__main__":
    main()
