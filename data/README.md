# How to update the website

Most content on **https://rohanjuneja.github.io** comes from the files
in this folder. Edit a file, commit, and push — the site updates automatically
in 1–2 minutes. You never need to touch `index.html`.

| File | Controls |
|------|----------|
| `profile.yml` | Photo, name, title, affiliation, red banner, biography, interests, education, social/contact icons |
| `news.yml` | The "News" section — short dated updates, newest first |
| `experience.yml` | Work / research timeline cards |
| `publications.yml` | **Auto-generated — do not edit.** See "Publications" below. |

> **Publications are different:** `publications.yml` is generated automatically
> from your **résumé** (`files/resume.pdf`) by a GitHub Action. You don't edit it.
> See the [Publications](#publications-automatic) section.

## Quick start

**Easiest (in the browser):** open the file on github.com → click the ✏️ pencil →
edit → **Commit changes**. That deploys it. No tools to install.

**Locally:**
```bash
git pull
# edit the .yml file
git add data/
git commit -m "Update publications"
git push
```
Then hard-refresh the site (Ctrl/Cmd + Shift + R).

## Publications (automatic)

The Publications section is **built from your résumé** — you do not edit
`data/publications.yml` by hand. On every push, a GitHub Action
(`build-publications.yml`) runs `scripts/build_publications.py`, which:

1. reads the "Publication Record" from `files/resume.pdf`,
2. auto-fetches each published paper's **DOI** (IEEE/ACM link) from Crossref,
3. picks up any slides/PDFs you uploaded (see below),
4. regenerates `data/publications.yml` and commits it.

### To add or change a paper
**Edit `files/resume.pdf`** (i.e. update your résumé) and push. The new paper
appears automatically — title, authors, venue, year, and status tags like
`[Under Review]` / `[Best Paper]` are all read from the résumé. Your name is
bolded automatically; `∗` equal-contribution markers become a footnote.

### To add slides, a local PDF, or extra links
Each paper has a folder `publications/<slug>/` (the `<slug>` is shown in the
build log and is the folder name). Drop files in and push:

- **`slides.pdf`** → a **SLIDES** button (viewable in-browser). Export `.pptx`
  to PDF so it can be viewed inline.
- **`paper.pdf`** → a **PDF** button.
- **`links.yml`** in that folder holds `doi`, `arxiv`, `code`, `video`. The `doi`
  is auto-filled; set/correct any field to pin it. Set `doi: ''` to force "no DOI".

### If the résumé parser gets something wrong
Edit `publications/overrides.yml` (keyed by slug) to fix a field or hide a paper.
This is rarely needed.

## Common edits

### Add a news update
Paste a block at the **top** of `news.yml` (newest first):
```yaml
- date: Jun 2026
  html: 'Paper accepted at <a href="https://example.com">ISCA 2026</a>!'
```
`html` allows links and `<strong>` emphasis.

### Add a job
Paste a block in `experience.yml` (top of the list = most recent):
```yaml
- title: Your Role
  company: Company Name
  url: https://company.com
  date: Jan 2026 – Present
  location: City, Country
  current: true          # filled timeline dot — use only on your latest role
  body_html: >-
    <ul>
    <li>Bullet point one.</li>
    <li>Bullet point two.</li>
    </ul>
```
`location` and `body_html` are optional.

### Edit your bio / banner
In `profile.yml`, each `- ` line under `bio_html:` is one paragraph.
To hide the red "on the job market" line:
```yaml
banner_html: ""
```

## Two rules to avoid breaking the page

1. **Use spaces, not tabs**, and keep new entries aligned exactly like the existing
   ones. YAML uses indentation to understand structure.
2. **If a value contains a colon `:` or starts with a quote**, wrap the whole value
   in single quotes:
   ```yaml
   title: 'CTScan: A CGRA-based Platform'
   ```

## If something looks blank

It's almost always a YAML typo. Two ways to find it:
- Every push runs an automatic check (see `.github/workflows/validate-data.yml`).
  If your YAML is malformed, the commit gets a ❌ on GitHub with the error.
- Or open the site, press **F12** → **Console**: `site-content.js` prints the exact
  file and error.
