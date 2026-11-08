import argparse
import html
import json
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime


def esc(value):
    return html.escape(str(value or ""), quote=True)


def safe_url(value):
    if not value:
        return ""

    value = str(value).strip()

    if value.startswith("//"):
        value = "https:" + value

    parsed = urlparse(value)

    if parsed.scheme in ("http", "https"):
        return value

    return ""


def generate_report(data, output):
    results = data.get("results", [])
    total = data.get("total_results", len(results))

    sources = sorted({
        str(item.get("source") or "Unknown source")
        for item in results
    })

    options = "".join(
        f'<option value="{esc(source)}">{esc(source)}</option>'
        for source in sources
    )

    cards = []

    for index, item in enumerate(results, 1):
        title = str(item.get("title") or "Untitled result")
        source = str(item.get("source") or "Unknown source")
        description = str(
            item.get("description") or "No description available."
        )
        metadata = item.get("metadata") or {}
        confidence_warning = (
            '<p style="background:#fff3cd;color:#856404;padding:9px;'
            'border-radius:6px;font-weight:bold;">'
            'LOW CONFIDENCE: AnimeTrace character candidates are not confirmed.</p>'
            if metadata.get("result_type") == "character_candidates"
            and metadata.get("not_confident") else ""
        )
        size = str(item.get("image_size") or "Unknown")

        page_url = safe_url(item.get("url"))
        original_url = safe_url(item.get("original_image"))
        thumbnail = safe_url(item.get("thumbnail"))

        search_text = (title + " " + source + " " + description).lower()

        image = (
            f'<img class="thumb" src="{esc(thumbnail)}" '
            f'alt="{esc(title)}" loading="lazy">'
            if thumbnail else
            '<div class="no-image">No thumbnail available</div>'
        )

        page_link = (
            f'<a href="{esc(page_url)}" target="_blank" '
            f'rel="noopener noreferrer">Open source page</a>'
            if page_url else ""
        )

        original_link = (
            f'<a href="{esc(original_url)}" target="_blank" '
            f'rel="noopener noreferrer">Original image</a>'
            if original_url else ""
        )

        cards.append(f"""
        <article class="card"
            data-search="{esc(search_text)}"
            data-source="{esc(source)}">

            <div class="image" onclick="previewImage(this)">
                {image}
            </div>

            <div class="details">
                <span class="number">RESULT {index}</span>
                <h2>{esc(title)}</h2>
                <p class="source">{esc(source)}</p>
                <p class="description">{esc(description)}</p>
                {confidence_warning}
                <p class="size">Image size: {esc(size)}</p>
                <div class="links">
                    {page_link}
                    {original_link}
                </div>
            </div>
        </article>
        """)

    search_url = safe_url(data.get("search_url"))

    search_link = (
        f'<a href="{esc(search_url)}" target="_blank" '
        f'rel="noopener noreferrer">Open Yandex search</a>'
        if search_url else ""
    )

    generated = datetime.now().strftime("%d %B %Y, %H:%M:%S")

    document = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<title>Reverse Image Search Report</title>

<style>
* {{ box-sizing: border-box; }}

body {{
    margin: 0;
    background: #101827;
    color: #e5e7eb;
    font-family: Arial, sans-serif;
}}

header {{
    padding: 25px 15px;
    background: #172554;
    text-align: center;
}}

header h1 {{ margin: 0 0 10px; }}

header p {{
    margin: 5px;
    color: #cbd5e1;
}}

.stats {{
    display: flex;
    justify-content: center;
    flex-wrap: wrap;
    gap: 12px;
    padding: 18px;
}}

.stat {{
    background: #1e293b;
    border: 1px solid #334155;
    padding: 15px 22px;
    border-radius: 10px;
    text-align: center;
}}

.stat strong {{
    display: block;
    font-size: 23px;
    color: #38bdf8;
}}

.stat span {{
    font-size: 12px;
    color: #cbd5e1;
}}

.toolbar {{
    max-width: 1000px;
    margin: 10px auto;
    padding: 10px 14px;
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
}}

.toolbar input, .toolbar select, .toolbar button {{
    padding: 12px;
    border-radius: 8px;
    border: 1px solid #475569;
    background: #1e293b;
    color: white;
    font-size: 14px;
}}

.toolbar input {{
    flex: 1;
    min-width: 180px;
}}

.toolbar select {{ flex: 1; min-width: 150px; }}

.toolbar button {{
    background: #075985;
    cursor: pointer;
}}

.container {{
    max-width: 1100px;
    margin: auto;
    padding: 10px 14px 35px;
}}

.gallery {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 15px;
}}

.card {{
    background: #1e293b;
    border: 1px solid #334155;
    border-radius: 12px;
    padding: 12px;
    overflow: hidden;
}}

.image {{
    height: 190px;
    display: flex;
    justify-content: center;
    align-items: center;
    background: #0f172a;
    border-radius: 8px;
    overflow: hidden;
    cursor: zoom-in;
}}

.thumb {{
    width: 100%;
    height: 100%;
    object-fit: contain;
}}

.no-image {{
    color: #94a3b8;
    font-size: 12px;
}}

.number {{
    display: inline-block;
    margin-top: 12px;
    color: #38bdf8;
    font-size: 11px;
    font-weight: bold;
}}

h2 {{
    font-size: 16px;
    overflow-wrap: anywhere;
}}

.source {{
    color: #86efac;
    font-size: 13px;
}}

.description {{
    color: #cbd5e1;
    font-size: 13px;
    line-height: 1.5;
}}

.size {{
    color: #94a3b8;
    font-size: 12px;
}}

.links {{
    display: flex;
    flex-wrap: wrap;
    gap: 12px;
    margin-top: 12px;
}}

a {{
    color: #38bdf8;
    font-size: 13px;
    text-decoration: none;
}}

a:hover {{ text-decoration: underline; }}

#count {{
    color: #94a3b8;
    font-size: 13px;
    margin: 10px 0;
}}

#preview {{
    display: none;
    position: fixed;
    z-index: 10;
    inset: 0;
    background: rgba(0,0,0,.94);
    justify-content: center;
    align-items: center;
    padding: 15px;
}}

#preview img {{
    max-width: 100%;
    max-height: 85vh;
    object-fit: contain;
}}

#preview button {{
    position: absolute;
    top: 15px;
    right: 20px;
    background: #334155;
    color: white;
    border: 0;
    padding: 12px 16px;
    border-radius: 8px;
    font-size: 18px;
}}

footer {{
    text-align: center;
    color: #94a3b8;
    padding: 20px;
    font-size: 12px;
}}

@media print {{
    body {{ background: white; color: black; }}
    header {{ background: white; color: black; }}
    header p {{ color: black; }}
    .toolbar, #preview, footer {{ display: none !important; }}
    .stats, .stat {{ background: white; color: black; }}
    .stat strong {{ color: black; }}
    .stat span {{ color: black; }}
    .gallery {{ display: block; }}
    .card {{
        break-inside: avoid;
        background: white;
        color: black;
        border: 1px solid #aaa;
        margin-bottom: 12px;
    }}
    .description, .size, .source {{ color: black; }}
    a {{ color: black; }}
}}
</style>
</head>

<body>

<header>
    <h1>Reverse Image Search Report</h1>
    <p>Search engine: {esc(data.get("engine", "Yandex"))}</p>
    <p>Generated: {esc(generated)}</p>
</header>

<section class="stats">
    <div class="stat">
        <strong>{total}</strong>
        <span>Total matches</span>
    </div>

    <div class="stat">
        <strong>{len(results)}</strong>
        <span>Saved results</span>
    </div>

    <div class="stat">
        <strong>{esc(data.get("engine", "Yandex"))}</strong>
        <span>Search engine</span>
    </div>
</section>

<div class="toolbar">
    <input id="search" type="search"
        placeholder="Search titles, websites or descriptions...">

    <select id="source">
        <option value="">All websites</option>
        {options}
    </select>

    <button onclick="window.print()">Print / Save PDF</button>
</div>

<div class="container">
    <p>{search_link}</p>
    <p id="count"></p>

    <div class="gallery" id="gallery">
        {''.join(cards) if cards else '<p>No results found.</p>'}
    </div>
</div>

<div id="preview" onclick="closePreview()">
    <button onclick="closePreview()">Close ✕</button>
    <img id="preview-img" src="" alt="Enlarged image">
</div>

<footer>
    Generated by Reverse Image Search CLI
</footer>

<script>
const searchBox = document.getElementById("search");
const sourceBox = document.getElementById("source");
const cards = Array.from(document.querySelectorAll(".card"));
const count = document.getElementById("count");

function filterResults() {{
    const query = searchBox.value.toLowerCase().trim();
    const source = sourceBox.value;
    let visible = 0;

    cards.forEach(card => {{
        const matchesText = card.dataset.search.includes(query);
        const matchesSource = !source || card.dataset.source === source;
        const show = matchesText && matchesSource;

        card.style.display = show ? "" : "none";

        if (show) visible++;
    }});

    count.textContent = visible + " of " + cards.length + " results shown";
}}

function previewImage(element) {{
    const img = element.querySelector("img");

    if (!img) return;

    document.getElementById("preview-img").src = img.src;
    document.getElementById("preview").style.display = "flex";
}}

function closePreview() {{
    document.getElementById("preview").style.display = "none";
}}

searchBox.addEventListener("input", filterResults);
sourceBox.addEventListener("change", filterResults);

document.addEventListener("keydown", event => {{
    if (event.key === "Escape") closePreview();
}});

filterResults();
</script>

</body>
</html>
"""

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8")
    return len(results)


def main():
    parser = argparse.ArgumentParser(
        description="Create an interactive reverse-image HTML report."
    )

    parser.add_argument("json_report", help="JSON report path")
    parser.add_argument("-o", "--output", help="HTML output path")

    args = parser.parse_args()

    source = Path(args.json_report).expanduser().resolve()

    if not source.is_file():
        parser.error(f"JSON report not found: {source}")

    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except Exception as error:
        parser.error(f"Could not read JSON report: {error}")

    if not isinstance(data, dict) or not isinstance(data.get("results", []), list):
        parser.error("Invalid reverse-image JSON report structure.")

    output = (
        Path(args.output).expanduser()
        if args.output else source.with_suffix(".html")
    )

    count = generate_report(data, output)

    print("\n[+] Interactive HTML report created")
    print(f"[+] Results: {count}")
    print(f"[+] File: {output.resolve()}")


if __name__ == "__main__":
    main()
