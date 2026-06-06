# How to update the website

Most content on **https://rohanjuneja.github.io** comes from the files
in this folder. Edit a file, commit, and push — the site updates automatically
in 1–2 minutes. You never need to touch `index.html`.

| File | Controls |
|------|----------|
| `profile.yml` | Photo, name, title, affiliation, red banner, biography, interests, education, social/contact icons |
| `news.yml` | The "News" section — short dated updates, newest first |
| `experience.yml` | **Auto-generated — do not edit.** See "Experience & Publications" below. |
| `publications.yml` | **Auto-generated — do not edit.** See "Experience & Publications" below. |

> **Experience and Publications are different:** `experience.yml` and
> `publications.yml` are generated automatically from your **résumé**
> (`files/resume.pdf`) by a GitHub Action. You don't edit them.
> See the [Experience & Publications](#experience--publications-automatic) section.

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

## Experience & Publications (automatic)

Both the **Experience** and **Publications** sections are **built from your
résumé** — you do not edit `data/experience.yml` or `data/publications.yml` by
hand. On every push, one GitHub Action (`build-from-resume.yml`) runs the two
build scripts and commits the regenerated files.

### Experience
`scripts/build_experience.py` reads the "Professional Experience" section of
`files/resume.pdf` (company, location, role, dates, bullet points; the most
recent role marked "Present" gets the filled timeline dot).

- **To add/change a role:** edit your résumé and push.
- **Company links and corrections:** the résumé has no URLs, so set each
  company's website in `experience/overrides.yml` (keyed by company slug). You
  can also correct a field or hide an entry there.

### Publications
`scripts/build_publications.py`:

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
Experience is auto-generated — **edit your résumé** (`files/resume.pdf`) and push.
See [Experience & Publications](#experience--publications-automatic) above. Set
the company link in `experience/overrides.yml`.

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
