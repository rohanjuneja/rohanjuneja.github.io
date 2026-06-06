#!/usr/bin/env python3
"""
build_experience.py — regenerate data/experience.yml from files/resume.pdf.

Parses the "Professional Experience" section of the resume into the timeline
cards shown on the site. Company/location and role/date are split using word
x-coordinates (the resume right-aligns location and dates). Company URLs aren't
in the resume, so they live in experience/overrides.yml (pre-filled, editable),
which can also correct any field or hide an entry.

Like the publications build, this runs automatically in CI. You can also run it:
  pip install -r scripts/requirements.txt && python scripts/build_experience.py

Flag: --dry-run (don't write).
"""

import argparse
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESUME = os.path.join(ROOT, "files", "resume.pdf")
OUT_YAML = os.path.join(ROOT, "data", "experience.yml")
OVERRIDES = os.path.join(ROOT, "experience", "overrides.yml")

START_HEADING = "Professional Experience"
# Section headings that mark the end of the experience block.
END_HEADINGS = ("Publication Record", "Education", "Teaching Experience",
                "Awards", "Skills", "Service")
BULLET = "◦"
MARKER = "•"


# --------------------------------------------------------------------------- #
# PDF -> lines (with word coordinates)
# --------------------------------------------------------------------------- #
def get_lines():
    """Return document-ordered lines as {text, words}, where words carry x/top."""
    import pdfplumber

    lines = []
    with pdfplumber.open(RESUME) as pdf:
        for page in pdf.pages:
            words = page.extract_words(use_text_flow=False)
            words.sort(key=lambda w: (w["top"], w["x0"]))
            cluster, top = [], None
            for w in words:
                if top is None or abs(w["top"] - top) <= 3:
                    cluster.append(w)
                    if top is None:
                        top = w["top"]
                else:
                    lines.append(cluster)
                    cluster, top = [w], w["top"]
            if cluster:
                lines.append(cluster)
    out = []
    for ws in lines:
        ws = sorted(ws, key=lambda w: w["x0"])
        out.append({"text": " ".join(w["text"] for w in ws), "words": ws})
    return out


def split_right(words, min_gap=40):
    """Split a line at its widest inter-word gap (the right-alignment gap)."""
    if not words:
        return "", None
    gaps = [(words[i + 1]["x0"] - words[i]["x1"], i) for i in range(len(words) - 1)]
    if gaps:
        gap, idx = max(gaps)
        if gap >= min_gap:
            left = " ".join(w["text"] for w in words[: idx + 1])
            right = " ".join(w["text"] for w in words[idx + 1:])
            return left.strip(), right.strip()
    return " ".join(w["text"] for w in words).strip(), None


# --------------------------------------------------------------------------- #
# Parsing
# --------------------------------------------------------------------------- #
def parse_experience(lines):
    texts = [l["text"].strip() for l in lines]
    try:
        start = next(i for i, t in enumerate(texts) if t.startswith(START_HEADING))
    except StopIteration:
        raise SystemExit("ERROR: '%s' heading not found in resume." % START_HEADING)

    end = len(lines)
    for i in range(start + 1, len(texts)):
        if any(texts[i].startswith(h) for h in END_HEADINGS):
            end = i
            break
    region = lines[start + 1 : end]
    rtexts = [l["text"].strip() for l in region]
    markers = [i for i, t in enumerate(rtexts) if t == MARKER]

    entries = []
    for j, p in enumerate(markers):
        if p - 1 < 0 or p + 1 >= len(region):
            continue
        company, location = split_right(region[p - 1]["words"])
        role, date = split_right(region[p + 1]["words"])
        nxt = (markers[j + 1] - 1) if j + 1 < len(markers) else len(region)
        bullets = parse_bullets([l["text"] for l in region[p + 2 : nxt]])
        entries.append({
            "company": company,
            "location": location,
            "title": role,
            "date": normalize_date(date),
            "current": bool(date and "present" in date.lower()),
            "bullets": bullets,
        })
    return entries


def parse_bullets(raw_lines):
    bullets = []
    for l in raw_lines:
        l = l.strip()
        if not l:
            continue
        if l.startswith(BULLET):
            bullets.append(l[len(BULLET):].strip())
        elif bullets:
            bullets[-1] += " " + l  # continuation of the previous bullet
    return bullets


def normalize_date(date):
    if not date:
        return date
    return re.sub(r"\s*-\s*", " – ", date.strip())  # hyphen range -> en dash


# --------------------------------------------------------------------------- #
# Formatting
# --------------------------------------------------------------------------- #
def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def esc(s):
    return s.replace("&", "&amp;")


def bullets_to_html(bullets):
    if not bullets:
        return None
    items = "\n".join("<li>%s</li>" % esc(b) for b in bullets)
    return "<ul>\n%s\n</ul>" % items


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    parsed = parse_experience(get_lines())
    if len(parsed) < 3:
        raise SystemExit("ERROR: parsed only %d experience entries — refusing to "
                         "overwrite. Check resume layout / parser." % len(parsed))

    overrides = {}
    if os.path.exists(OVERRIDES):
        with open(OVERRIDES) as f:
            overrides = yaml.safe_load(f) or {}

    out_entries = []
    manifest = []
    for e in parsed:
        slug = slugify(e["company"])
        ov = overrides.get(slug, {}) if isinstance(overrides, dict) else {}
        if ov.get("exclude"):
            manifest.append((slug, e, "excluded"))
            continue
        for k in ("company", "title", "location", "date", "url"):
            if k in ov:
                e[k] = ov[k]
        if "current" in ov:
            e["current"] = ov["current"]

        entry = {"title": e["title"], "company": e["company"]}
        url = ov.get("url") or e.get("url")
        if url:
            entry["url"] = url
        entry["date"] = e["date"]
        if e.get("location"):
            entry["location"] = e["location"]
        if e.get("current"):
            entry["current"] = True
        body = ov["body_html"] if "body_html" in ov else bullets_to_html(e["bullets"])
        if body:
            entry["body_html"] = body
        out_entries.append(entry)
        manifest.append((slug, e, "url" if url else "no-url"))

    header = (
        "# =============================================================================\n"
        "# AUTO-GENERATED by scripts/build_experience.py from files/resume.pdf.\n"
        "# DO NOT EDIT BY HAND. To change experience:\n"
        "#   * add/edit a role     -> edit files/resume.pdf (Professional Experience)\n"
        "#   * set a company link  -> edit experience/overrides.yml\n"
        "#   * fix a misparse/hide -> edit experience/overrides.yml\n"
        "# The GitHub Action regenerates this file automatically on push.\n"
        "# =============================================================================\n"
    )

    print("\n=== Experience manifest (%d entries) ===" % len(out_entries))
    for slug, e, status in manifest:
        print("  %-34s %-9s %-22s %s%s"
              % (slug, status, e["date"], e["title"][:28],
                 " [current]" if e.get("current") else ""))

    if args.dry_run:
        print("\n[dry-run] not writing %s" % OUT_YAML)
        return

    with open(OUT_YAML, "w") as f:
        f.write(header)
        yaml.safe_dump(out_entries, f, allow_unicode=True, sort_keys=False,
                       default_flow_style=False, width=1000)
    print("\nWrote %s" % OUT_YAML)


if __name__ == "__main__":
    main()
