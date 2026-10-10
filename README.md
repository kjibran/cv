# Academic CV website

My academic CV as a fast, text-first website, with a PDF version built from the same data.

**Live site: [kjibran.github.io/cv](https://kjibran.github.io/cv/)**

The repository is also a template. If you are a researcher, you can have the same kind of site
running in about fifteen minutes, free, with no web development needed. You edit two text files,
push, and GitHub builds the website and the PDF for you.

## What you get

- A main page with your photo, a short bio, profile links and the full CV, with dates in the margin.
- A publications page with every paper, grouped by type and year, your name in bold.
- A chart of publications per year, redrawn from your data on every update.
- A PDF CV generated from the same data, so the website and the PDF never disagree.
- Light and dark mode, readable on phones, no tracking cookies.
- Search engine basics built in: page titles and descriptions, structured data (schema.org),
  sitemap, link previews.
- Your email address is encoded in the page, so spam bots cannot harvest it.
- A weekly check that tells you when a link in your CV breaks.

The pages load no frameworks. The main page is a single HTML file of about 70 KB, plus the font.

## Make your own in six steps

You need a GitHub account. Nothing has to be installed on your computer.

1. **Copy the template.** Click **Use this template** at the top of this page, then
   **Create a new repository**. Name it `cv` (your site will be at `https://<username>.github.io/cv/`).
   Keep it public.
2. **Turn on GitHub Pages.** In your new repository go to **Settings > Pages** and set
   **Source** to **GitHub Actions**.
3. **Replace the photo.** Delete `data/photo.jpg` and upload your own with the same name
   (**Add file > Upload files** in the `data` folder). Square works best. The build turns it grey
   and resizes it. To show no photo, set `photo: ""` in `data/profile.yaml`.
4. **Edit `data/profile.yaml`.** Open it on GitHub and click the pencil icon. Change `site.url`
   to your address, then your name, bio, links, positions and so on. Every section is optional.
   Delete a section and it disappears from the site and the PDF.
5. **Edit `data/publications.yaml`.** Replace the entries with your own. Mark the papers for the
   main page with `selected: true`.
6. **Commit.** The site builds and goes live in a few minutes. Follow the progress under the
   **Actions** tab. Then add the address to the **About** box of the repository (the gear icon),
   so visitors find the live site.

From then on, every change you commit to `data/` updates the website and the PDF.

## The two data files

### data/profile.yaml

Everything except the publications. A few fields need explaining.

| Field | What it does |
|---|---|
| `site.url` | The address of the site, ending with `/`. Used for search engines and link previews. |
| `site.title` | The text in the browser tab and in search results. |
| `site.goatcounter` | Your [GoatCounter](https://www.goatcounter.com) code for privacy-friendly visitor statistics. `""` turns statistics off. |
| `site.pdf_name` | The file name of the PDF, for example `Firstname_Lastname_CV.pdf`. |
| `person.highlight_name` | How your name is written in author lists, for example `Khan, J.`. It is shown in bold. |
| `person.email` | Shown as an encoded link on the website and as plain text in the PDF. |
| `links` | The icon row. `url: PDF` links to the generated PDF, `url: EMAIL` to your email. |
| `selected_publications` | The heading and the sentences around the selected papers on the main page. |

Icons available for `links`: `cv`, `mail`, `orcid`, `scholar`, `wos`, `scopus`, `researchgate`,
`zenodo`, `linkedin`, `github`, `portfolio`. To add another, see `engine/icons/LICENSES.md`.

Text is plain text. To add a link inside a sentence, write `[text](https://...)`. Chemical formulas
such as NO2, PM2.5 and CO2 get subscripts automatically.

### data/publications.yaml

One entry per publication, in the order you want them listed within each type (newest first works
best).

```yaml
- type: journal            # journal, proceedings, chapter or report
  year: 2025
  authors: "Khan, J., Jensen, S. S., & Ketzel, M."
  title: "Title of the paper"
  venue: "Atmosphere, 16(12), 1346"
  note: "Shared first author"        # optional
  selected: true                      # optional, shows the paper on the main page
  links:                              # optional, as many as you like
    - {label: "DOI", url: "https://doi.org/10.3390/..."}
    - {label: "Code and data", url: "https://doi.org/10.5281/zenodo..."}
```

Put quotes around text that contains a colon. If something is wrong in a file, the build stops
with a message that names the entry, and the live site stays as it was.

## Working on your own computer (optional)

With [Git](https://git-scm.com) and [uv](https://docs.astral.sh/uv/) installed:

```bash
git clone https://github.com/<username>/cv.git
cd cv
uv run python build.py --no-pdf
uv run python -m http.server 8765 -d site
```

Open http://localhost:8765. After each edit, run the build again and refresh.

The PDF needs the Pango library. On Linux and in WSL, install it with
`sudo apt-get install libpango-1.0-0 libpangoft2-1.0-0`, then run `uv run python build.py`.
On macOS, `brew install pango`. Without it, the build skips the PDF and says so. GitHub always
builds the PDF.

## How it works

```
data/profile.yaml          your CV
data/publications.yaml     your publications
data/photo.jpg             your photo
engine/templates/          page layouts (main page, publications page, PDF)
engine/fonts/              Source Serif 4, served from the site itself
engine/icons/icons.json    the icons, inlined into the page as SVG
build.py                   reads data/, writes the finished site into site/
.github/workflows/         deploy.yml builds and publishes on every push,
                           links.yml checks all links every Monday
```

`build.py` uses [Jinja](https://jinja.palletsprojects.com) for the pages,
[Pillow](https://python-pillow.org) for the photo and
[WeasyPrint](https://weasyprint.org) for the PDF. The `site/` folder is generated and never
committed.

To change colours or spacing, edit the CSS at the top of `engine/templates/base.html.j2`.

## Using your own domain

Buy a domain from any registrar. In **Settings > Pages > Custom domain**, enter it and follow
GitHub's instructions for the DNS records. Then change `site.url` in `data/profile.yaml` and push.

## Credits and licence

The layout of the top block is inspired by [Pascal Michaillat's website](https://pascalmichaillat.org).
Font: [Source Serif 4](https://github.com/adobe-fonts/source-serif) by Adobe (SIL Open Font
License). Icons: [Academicons](https://github.com/jpswalsh/academicons) (SIL Open Font License)
and [Tabler Icons](https://tabler.io/icons) (MIT).

The code and layout are MIT licensed, see [LICENSE](LICENSE). The content of `data/` (my CV
text, publication list and photo) is not covered by the licence. Please replace it with your own.
