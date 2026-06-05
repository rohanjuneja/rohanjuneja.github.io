# How to update the website

All the content on **https://rohanjuneja.github.io** comes from the three files
in this folder. Edit a file, commit, and push — the site updates automatically
in 1–2 minutes. You never need to touch `index.html`.

| File | Controls |
|------|----------|
| `profile.yml` | Photo, name, title, affiliation, red banner, biography, interests, education, social/contact icons |
| `news.yml` | The "News" section — short dated updates, newest first |
| `experience.yml` | Work / research timeline cards |
| `publications.yml` | Papers, grouped into Conferences / Journals / Chip Tapeouts |

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

## Common edits

### Add a publication
Paste a block under the right `entries:` list in `publications.yml`:
```yaml
      - badge: ISCA
        title: Your Paper Title Here
        authors_html: '<u><strong>Rohan Juneja</strong></u>, Co Author, Tulika Mitra'
        venue_html: 'In International Symposium on Computer Architecture (<strong>ISCA</strong>) 2026'
        links:
          - {label: ABS, url: https://arxiv.org/abs/xxxx}
          - {label: PDF, url: /publication/yourpaper.pdf}
```
- Wrap your own name as `<u><strong>Rohan Juneja</strong></u>`.
- `venue_html` and `links` are optional — delete those lines if you don't need them.
- `url: '#'` makes a greyed-out placeholder button.
- For a PDF: drop the file in the `publication/` folder and link `/publication/yourpaper.pdf`.
- `badge: ''` (empty) shows no venue tag on the left.
- Add `divider_before: true` to draw a horizontal line above an entry.

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
