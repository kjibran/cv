"""Build the CV website and the PDF from the files in data/.

    uv run python build.py           # website and PDF into site/
    uv run python build.py --no-pdf  # website only (faster, no system libraries needed)

Everything you normally edit is in data/. The engine/ folder holds the
layout, fonts and icons.
"""

from __future__ import annotations

import base64
import html
import json
import re
import shutil
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from markupsafe import Markup
from PIL import Image, ImageDraw, ImageOps

ROOT = Path(__file__).parent
DATA = ROOT / "data"
ENGINE = ROOT / "engine"
OUT = ROOT / "site"

TYPES = {  # order used on the publications page, in the chart and in the PDF
    "journal": "Journal articles",
    "proceedings": "Conference proceedings",
    "chapter": "Book chapters",
    "report": "Reports",
}
TYPE_SINGULAR = {
    "journal": "journal article",
    "proceedings": "conference paper",
    "chapter": "book chapter",
    "report": "report",
}


class DataError(Exception):
    pass


# --------------------------------------------------------------------------- data


def load_data() -> tuple[dict, list[dict]]:
    profile = yaml.safe_load((DATA / "profile.yaml").read_text(encoding="utf-8"))
    pubs = yaml.safe_load((DATA / "publications.yaml").read_text(encoding="utf-8")) or []

    for key in ("site", "person", "links"):
        if key not in profile:
            raise DataError(f"profile.yaml: missing section '{key}'")
    for key in ("url", "pdf_name"):
        if not profile["site"].get(key):
            raise DataError(f"profile.yaml: site.{key} is empty")
    for key, default in (("title", profile["person"].get("name", "")), ("source_repo", ""), ("goatcounter", ""),
                         ("google_verification", ""), ("language", "en"), ("timezone", "UTC")):
        profile["site"].setdefault(key, default)
    for key in ("title", "location", "photo", "highlight_name", "email"):
        profile["person"].setdefault(key, "")
    if not profile["site"]["url"].endswith("/"):
        profile["site"]["url"] += "/"
    for key in ("name", "bio"):
        if not profile["person"].get(key):
            raise DataError(f"profile.yaml: person.{key} is empty")

    for i, p in enumerate(pubs, 1):
        where = f"publications.yaml, entry {i} ({str(p.get('title', ''))[:50]!r})"
        for key in ("type", "year", "authors", "title"):
            if not p.get(key):
                raise DataError(f"{where}: '{key}' is missing")
        if p["type"] not in TYPES:
            raise DataError(f"{where}: type must be one of {', '.join(TYPES)}")
        p["year"] = int(p["year"])
        p.setdefault("venue", "")
        p.setdefault("note", "")
        p.setdefault("links", [])
        p.setdefault("selected", False)
    return profile, pubs


# ------------------------------------------------------------------ text helpers

CHEM = [
    (re.compile(r"\bPM2\.5\b"), "PM<sub>2.5</sub>"),
    (re.compile(r"\bPM10\b"), "PM<sub>10</sub>"),
    (re.compile(r"\bNO2\b"), "NO<sub>2</sub>"),
    (re.compile(r"\bNOx\b"), "NO<sub>x</sub>"),
    (re.compile(r"\bCO2\b"), "CO<sub>2</sub>"),
    (re.compile(r"\bO3\b"), "O<sub>3</sub>"),
]


def rich(text: object) -> Markup:
    """Escape plain text, then add subscripts to chemical formulas."""
    out = html.escape(str(text or ""), quote=False)
    for pattern, repl in CHEM:
        out = pattern.sub(repl, out)
    return Markup(out)


def make_authors(highlight: str):
    def authors(text: str) -> Markup:
        out = str(rich(text))
        if highlight:
            name = html.escape(highlight, quote=False)
            out = out.replace(name, f"<strong>{name}</strong>")
        return Markup(out)

    return authors


def encode_email(address: str) -> str:
    """Reversed and base64-encoded. A small script turns it back into a link."""
    return base64.b64encode(address[::-1].encode()).decode()


# ------------------------------------------------------------------------ icons


def load_icons() -> dict:
    return json.loads((ENGINE / "icons" / "icons.json").read_text(encoding="utf-8"))


def make_icon(icons: dict):
    def icon(name: str, cls: str = "icon") -> Markup:
        spec = icons.get(name)
        if spec is None:
            raise DataError(f"Unknown icon '{name}'. Available: {', '.join(sorted(icons))}")
        paths = "".join(
            f'<path d="{p["d"]}"' + (f' transform="{p["transform"]}"' if p.get("transform") else "") + "/>"
            for p in spec["paths"]
        )
        if spec.get("stroke"):
            paint = 'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"'
        else:
            paint = 'fill="currentColor"'
        return Markup(
            f'<svg class="{cls}" viewBox="{spec["viewBox"]}" {paint} aria-hidden="true" focusable="false">{paths}</svg>'
        )

    return icon


# ------------------------------------------------------------------------ chart


def chart_svg(pubs: list[dict]) -> Markup:
    """Stacked bar chart of publications per year and type, as inline SVG."""
    counts = Counter((p["year"], p["type"]) for p in pubs)
    years = list(range(min(p["year"] for p in pubs), max(p["year"] for p in pubs) + 1))
    totals = {y: sum(counts[(y, t)] for t in TYPES) for y in years}
    top = max(totals.values())
    step = 2 if top <= 12 else 5
    ymax = -(-top // step) * step

    width, height = 640, 230
    left, right, ptop, bottom = 32, 8, 10, 28
    plot_w, plot_h = width - left - right, height - ptop - bottom
    slot = plot_w / len(years)
    bar = slot * 0.62

    def y_of(v: float) -> float:
        return ptop + plot_h - v / ymax * plot_h

    parts = []
    for v in range(0, ymax + 1, step):
        y = y_of(v)
        parts.append(f'<line class="grid" x1="{left}" x2="{width - right}" y1="{y:.1f}" y2="{y:.1f}"/>')
        parts.append(f'<text class="tick" x="{left - 6}" y="{y + 4:.1f}" text-anchor="end">{v}</text>')
    for i, year in enumerate(years):
        x = left + i * slot + (slot - bar) / 2
        acc = 0
        for t in TYPES:
            n = counts[(year, t)]
            if not n:
                continue
            y0, y1 = y_of(acc), y_of(acc + n)
            label = f"{year}: {n} {TYPE_SINGULAR[t]}{'s' if n > 1 else ''}"
            parts.append(
                f'<rect class="s-{t}" x="{x:.1f}" y="{y1:.1f}" width="{bar:.1f}" height="{y0 - y1:.1f}">'
                f"<title>{label}</title></rect>"
            )
            acc += n
        show_label = len(years) <= 14 or (year - years[0]) % 2 == 0
        if show_label:
            parts.append(
                f'<text class="tick" x="{x + bar / 2:.1f}" y="{height - 8}" text-anchor="middle">{year}</text>'
            )

    used = [t for t in TYPES if any(p["type"] == t for p in pubs)]
    desc = ", ".join(f"{sum(1 for p in pubs if p['type'] == t)} {TYPES[t].lower()}" for t in used)
    svg = (
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="Publications per year by type, {years[0]} to {years[-1]}: {desc}">'
        + "".join(parts)
        + "</svg>"
    )
    legend = "".join(
        f'<span class="key"><span class="swatch s-{t}"></span>{TYPES[t]} '
        f"({sum(1 for p in pubs if p['type'] == t)})</span>"
        for t in used
    )
    return Markup(f'{svg}<div class="legend">{legend}</div>')


# ------------------------------------------------------------------------ images


def process_photo(profile: dict) -> dict | None:
    """Grey, square, two sizes in WebP plus a JPEG for link previews."""
    name = profile["person"].get("photo")
    if not name:
        return None
    src = DATA / name
    if not src.exists():
        print(f"  note: {src.relative_to(ROOT)} not found, building without a photo")
        return None
    img = ImageOps.exif_transpose(Image.open(src))
    img = ImageOps.grayscale(img)
    side = min(img.size)
    img = ImageOps.fit(img, (side, side), method=Image.Resampling.LANCZOS, centering=(0.5, 0.35))
    for px in (200, 400):
        img.resize((px, px), Image.Resampling.LANCZOS).save(OUT / f"photo-{px}.webp", quality=82, method=6)
    img.resize((600, 600), Image.Resampling.LANCZOS).convert("RGB").save(OUT / "photo.jpg", quality=85)
    return {"small": "photo-200.webp", "large": "photo-400.webp", "jpg": "photo.jpg"}


def initials(name: str) -> str:
    words = [w for w in re.split(r"\s+", name) if w]
    return (words[0][0] + (words[-1][0] if len(words) > 1 else "")).upper()


def write_favicon(profile: dict) -> None:
    letters = html.escape(initials(profile["person"]["name"]))
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
        '<rect width="64" height="64" rx="12" fill="#2b2b2b"/>'
        f'<text x="32" y="43" font-family="Georgia, serif" font-size="30" fill="#fff" '
        f'text-anchor="middle">{letters}</text></svg>'
    )
    (OUT / "favicon.svg").write_text(svg, encoding="utf-8")
    img = Image.new("RGB", (180, 180), "#2b2b2b")
    ImageDraw.Draw(img).text((90, 92), letters, fill="white", anchor="mm", font_size=84)
    img.save(OUT / "apple-touch-icon.png")


# ------------------------------------------------------------------------ SEO


def person_jsonld(profile: dict, photo: dict | None) -> Markup:
    person, site = profile["person"], profile["site"]
    same_as = [
        link["url"]
        for link in profile["links"]
        if link["url"].startswith("http") and "search?" not in link["url"]
    ]
    data = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": person["name"],
        "url": site["url"],
        "description": person.get("title", ""),
        "sameAs": same_as,
    }
    if person.get("location"):
        data["address"] = {"@type": "PostalAddress", "addressLocality": person["location"]}
    positions = profile.get("positions") or []
    current = [p for p in positions if "present" in str(p.get("period", ""))]
    if current:
        data["jobTitle"] = current[0]["role"] if len(current) == 1 else [p["role"] for p in current]
        orgs = []
        for p in current:
            parts = [s.strip() for s in p["place"].split(",")]
            org = next((s for s in parts if "University" in s or "Institute" in s), parts[0])
            orgs.append({"@type": "Organization", "name": org})
        data["affiliation"] = orgs
    if photo:
        data["image"] = site["url"] + photo["jpg"]
    return Markup(json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))


def pubs_jsonld(profile: dict, pubs: list[dict]) -> Markup:
    person = profile["person"]
    articles = []
    for p in pubs:
        item = {
            "@type": "ScholarlyArticle" if p["type"] in ("journal", "proceedings") else "CreativeWork",
            "name": p["title"],
            "datePublished": str(p["year"]),
        }
        doi = next((link["url"] for link in p["links"] if link["label"] == "DOI"), None)
        if doi:
            item["url"] = doi
        if p["venue"]:
            item["isPartOf"] = p["venue"].split(",")[0]
        articles.append(item)
    data = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": f"Publications of {person['name']}",
        "url": profile["site"]["url"] + "publications/",
        "about": {"@type": "Person", "name": person["name"], "url": profile["site"]["url"]},
        "hasPart": articles,
    }
    return Markup(json.dumps(data, ensure_ascii=False).replace("</", "<\\/"))


def write_seo_files(profile: dict, today: str) -> None:
    base = profile["site"]["url"]
    urls = [base, base + "publications/"]
    body = "".join(f"  <url><loc>{u}</loc><lastmod>{today}</lastmod></url>\n" for u in urls)
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + body + "</urlset>\n",
        encoding="utf-8",
    )
    (OUT / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {base}sitemap.xml\n", encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")


# ------------------------------------------------------------------------ PDF


def build_pdf(env: Environment, ctx: dict) -> bool:
    try:
        from weasyprint import HTML
    except (ImportError, OSError) as exc:
        print(f"  note: PDF skipped, WeasyPrint is not available here ({exc.__class__.__name__}).")
        print("        GitHub builds it on every push. Locally: build.py --no-pdf to silence this.")
        return False
    page = env.get_template("cv_pdf.html.j2").render(**ctx, fonts_url=(ENGINE / "fonts").as_uri() + "/")
    HTML(string=page, base_url=str(OUT)).write_pdf(OUT / ctx["site"]["pdf_name"])
    return True


# ------------------------------------------------------------------------ main


def main() -> int:
    make_pdf = "--no-pdf" not in sys.argv
    try:
        profile, pubs = load_data()
    except (DataError, yaml.YAMLError) as exc:
        print(f"Build stopped: {exc}")
        return 1

    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "fonts").mkdir(parents=True)
    (OUT / "publications").mkdir()
    for font in (ENGINE / "fonts").glob("*.woff2"):
        shutil.copy(font, OUT / "fonts" / font.name)

    tz = ZoneInfo(profile["site"].get("timezone") or "UTC")
    now = datetime.now(tz)
    photo = process_photo(profile)
    write_favicon(profile)

    env = Environment(
        loader=FileSystemLoader(ENGINE / "templates"),
        undefined=StrictUndefined,
        autoescape=True,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    icons = load_icons()
    env.filters["rich"] = rich
    env.filters["authors"] = make_authors(profile["person"].get("highlight_name", ""))
    env.globals["icon"] = make_icon(icons)

    by_type = {t: [p for p in pubs if p["type"] == t] for t in TYPES}
    by_type = {t: items for t, items in by_type.items() if items}
    grouped = {
        t: [(y, [p for p in items if p["year"] == y]) for y in sorted({p["year"] for p in items}, reverse=True)]
        for t, items in by_type.items()
    }
    sel = profile.get("selected_publications") or {}
    ctx = {
        "site": profile["site"],
        "person": profile["person"],
        "p": profile,
        "links": profile["links"],
        "email_code": encode_email(profile["person"].get("email", "")),
        "photo": photo,
        "pubs": pubs,
        "selected": [p for p in pubs if p["selected"]],
        "selected_text": {
            "heading": sel.get("heading", "Selected publications"),
            "intro": sel.get("intro", ""),
            "more": sel.get("more", "All {total} publications are on the publications page.").format(
                total=len(pubs)
            ),
        },
        "types": TYPES,
        "by_type": by_type,
        "grouped": grouped,
        "chart": chart_svg(pubs) if pubs else Markup(""),
        "updated": f"{now.day} {now:%B %Y}",
        "updated_iso": now.date().isoformat(),
        "year_span": (min(p["year"] for p in pubs), max(p["year"] for p in pubs)) if pubs else None,
    }

    for template, target, root, extra in (
        ("index.html.j2", OUT / "index.html", "", {"jsonld": person_jsonld(profile, photo)}),
        ("publications.html.j2", OUT / "publications" / "index.html", "../", {"jsonld": pubs_jsonld(profile, pubs)}),
    ):
        page = env.get_template(template).render(**ctx, **extra, root=root)
        target.write_text(page, encoding="utf-8")

    write_seo_files(profile, ctx["updated_iso"])
    pdf_done = make_pdf and build_pdf(env, ctx)

    selected = len(ctx["selected"])
    print(f"Built site/ with {len(pubs)} publications ({selected} selected)" + (", PDF included." if pdf_done else "."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
