import argparse
import html
import json
import mimetypes
from pathlib import Path
import shutil
import sys
import socket
import subprocess
import time
from urllib.parse import urlparse, quote
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx


def esc(value):
    return html.escape(str(value or ""), quote=True)


def safe_url(value):
    value = str(value or "").strip()
    if value.startswith("//"):
        value = "https:" + value
    parsed = urlparse(value)
    return value if parsed.scheme in ("http", "https") else ""


def download_thumbnail(client, index, url, folder):
    if not url:
        return index, ""

    url = safe_url(url)
    if not url:
        return index, ""

    try:
        response = client.get(url)
        response.raise_for_status()

        content_type = response.headers.get("content-type", "").split(";")[0]
        if not content_type.startswith("image/"):
            return index, ""

        extension = mimetypes.guess_extension(content_type) or ".jpg"
        if extension == ".jpe":
            extension = ".jpg"

        filename = f"thumb_{index:03d}{extension}"
        (folder / filename).write_bytes(response.content)

        return index, filename

    except Exception as error:
        print(f"[!] Thumbnail {index} failed: {error}")
        return index, ""


def main():
    parser = argparse.ArgumentParser(
        description="Create an HTML report with locally downloaded thumbnails."
    )
    parser.add_argument("json_report", help="Existing JSON report")
    parser.add_argument("-o", "--output", help="HTML output file")
    parser.add_argument("-w", "--workers", type=int, default=6,
                        help="Concurrent downloads (default: 6)")
    parser.add_argument("--no-serve", action="store_true",
                        help="Publish report without starting PHP server")
    args = parser.parse_args()

    source = Path(args.json_report).expanduser().resolve()

    if not source.is_file():
        parser.error(f"Report not found: {source}")

    if not 1 <= args.workers <= 12:
        parser.error("Workers must be between 1 and 12.")

    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except Exception as error:
        parser.error(f"Invalid JSON: {error}")

    results = data.get("results", [])
    if not isinstance(results, list):
        parser.error("Invalid results list.")

    output = (
        Path(args.output).expanduser().resolve()
        if args.output else source.with_name(source.stem + "_local.html")
    )

    image_folder = output.parent / (output.stem + "_images")
    image_folder.mkdir(parents=True, exist_ok=True)

    print(f"[+] Downloading thumbnails for {len(results)} results...")

    downloaded = {}

    with httpx.Client(
        timeout=25,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0"}
    ) as client:

        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            tasks = [
                executor.submit(
                    download_thumbnail,
                    client,
                    index,
                    item.get("thumbnail", ""),
                    image_folder
                )
                for index, item in enumerate(results, 1)
            ]

            for task in as_completed(tasks):
                index, filename = task.result()
                downloaded[index] = filename

    cards = []

    for index, item in enumerate(results, 1):
        title = item.get("title") or "Untitled result"
        website = item.get("source") or "Unknown source"
        description = item.get("description") or "No description available."
        metadata = item.get("metadata") or {}
        confidence_warning = (
            '<p style="background:#fff3cd;color:#856404;padding:9px;'
            'border-radius:6px;font-weight:bold;">'
            'LOW CONFIDENCE: AnimeTrace character candidates are not confirmed.</p>'
            if metadata.get("result_type") == "character_candidates"
            and metadata.get("not_confident") else ""
        )
        size = item.get("image_size") or "Unknown"

        filename = downloaded.get(index, "")

        if filename:
            image = (
                f'<img class="thumb" src="{esc(image_folder.name + "/" + filename)}" '
                f'alt="{esc(title)}" loading="lazy">'
            )
        else:
            image = '<div class="missing">Thumbnail unavailable</div>'

        page_url = safe_url(item.get("url"))
        original_url = safe_url(item.get("original_image"))

        links = ""
        if page_url:
            links += (
                f'<a href="{esc(page_url)}" target="_blank" '
                f'rel="noopener noreferrer">Source page</a>'
            )
        if original_url:
            links += (
                f'<a href="{esc(original_url)}" target="_blank" '
                f'rel="noopener noreferrer">Original image</a>'
            )

        search_text = (str(title) + " " + str(website) + " " + str(description)).lower()

        cards.append(f"""
        <article class="card"
            data-search="{esc(search_text)}"
            data-source="{esc(website)}">
            <div class="image" onclick="preview(this)">
                {image}
            </div>
            <span class="number">RESULT {index}</span>
            <h2>{esc(title)}</h2>
            <p class="source">{esc(website)}</p>
            <p>{esc(description)}</p>
            {confidence_warning}
            <p class="size">Image size: {esc(size)}</p>
            <div class="links">{links}</div>
        </article>
        """)

    websites = sorted({
        str(item.get("source") or "Unknown source")
        for item in results
    })

    options = "".join(
        f'<option value="{esc(site)}">{esc(site)}</option>'
        for site in websites
    )

    document = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Local Reverse Image Report</title>
<style>
* {{box-sizing:border-box}}
body {{margin:0;background:#101827;color:#e5e7eb;font-family:Arial,sans-serif}}
header {{background:#172554;padding:24px;text-align:center}}
.toolbar {{display:flex;gap:10px;flex-wrap:wrap;padding:15px;max-width:1100px;margin:auto}}
input,select,button {{padding:12px;border-radius:8px;border:1px solid #475569;background:#1e293b;color:white}}
input {{flex:1;min-width:180px}}
select {{flex:1;min-width:140px}}
button {{background:#075985}}
.container {{max-width:1100px;margin:auto;padding:10px 14px}}
.gallery {{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:15px}}
.card {{background:#1e293b;border:1px solid #334155;border-radius:12px;padding:12px;overflow:hidden}}
.image {{height:190px;background:#0f172a;border-radius:8px;display:flex;align-items:center;justify-content:center;cursor:zoom-in;overflow:hidden}}
.thumb {{width:100%;height:100%;object-fit:contain}}
.missing {{color:#94a3b8}}
.number {{display:block;color:#38bdf8;font-size:11px;margin-top:12px}}
h2 {{font-size:16px;overflow-wrap:anywhere}}
p {{font-size:13px;line-height:1.5;color:#cbd5e1}}
.source {{color:#86efac}}
.size {{color:#94a3b8}}
.links {{display:flex;gap:12px;flex-wrap:wrap}}
a {{color:#38bdf8;font-size:13px;text-decoration:none}}
#preview {{display:none;position:fixed;inset:0;background:#000e;z-index:5;align-items:center;justify-content:center;padding:15px}}
#preview img {{max-width:100%;max-height:85vh;object-fit:contain}}
#preview button {{position:absolute;right:15px;top:15px}}
@media print {{
 body {{background:white;color:black}}
 header {{background:white;color:black}}
 .toolbar,#preview {{display:none!important}}
 .gallery {{display:block}}
 .card {{background:white;color:black;break-inside:avoid;border:1px solid #aaa;margin-bottom:12px}}
 p {{color:black}}
}}
</style>
</head>
<body>
<header>
<h1>Reverse Image Search Report</h1>
<p>Engine: {esc(data.get("engine", "Yandex"))}</p>
<p>Total matches: {len(results)} | Local thumbnails: {len([x for x in downloaded.values() if x])}</p>
</header>
<div class="toolbar">
<input id="search" type="search" placeholder="Search results...">
<select id="source">
<option value="">All websites</option>{options}
</select>
<button onclick="window.print()">Print / Save PDF</button>
</div>
<div class="container">
<p id="count"></p>
<div class="gallery">{''.join(cards)}</div>
</div>
<div id="preview" onclick="closePreview()">
<button onclick="closePreview()">Close ✕</button>
<img id="large" alt="Image preview">
</div>
<script>
const cards=[...document.querySelectorAll(".card")];
const search=document.getElementById("search");
const source=document.getElementById("source");
function filter() {{
 let n=0;
 cards.forEach(c=>{{
  let show=c.dataset.search.includes(search.value.toLowerCase()) &&
    (!source.value || c.dataset.source===source.value);
  c.style.display=show?"":"none";
  if(show)n++;
 }});
 document.getElementById("count").textContent=n+" of "+cards.length+" results shown";
}}
function preview(el) {{
 const img=el.querySelector("img");
 if(!img)return;
 document.getElementById("large").src=img.src;
 document.getElementById("preview").style.display="flex";
}}
function closePreview() {{
 document.getElementById("preview").style.display="none";
}}
search.addEventListener("input",filter);
source.addEventListener("change",filter);
document.addEventListener("keydown",e=>{{if(e.key==="Escape")closePreview()}});
filter();
</script>
</body>
</html>
"""

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(document, encoding="utf-8")

    # Publish report and thumbnails to Android Downloads.
    download_dir = Path.home() / "storage/shared/Download"
    published_output = download_dir / output.name

    try:
        download_dir.mkdir(parents=True, exist_ok=True)

        if output.resolve() != published_output.resolve():
            shutil.copy2(output, published_output)

        published_images = download_dir / image_folder.name

        if image_folder.resolve() != published_images.resolve():
            shutil.copytree(
                image_folder,
                published_images,
                dirs_exist_ok=True
            )

        print(f"[+] Published HTML: {published_output}")
        print(f"[+] Published images: {published_images}")

        # Start the shared, centrally managed PHP server.
        if not args.no_serve:
            server_script = Path(__file__).with_name(
                "reverse_image_server.py"
            )

            completed = subprocess.run(
                [sys.executable, str(server_script), "start"],
                check=False
            )

            if completed.returncode == 0:
                print(
                    "\n[+] OPEN IN BROWSER: "
                    f"http://127.0.0.1:8765/{quote(published_output.name)}"
                )
            else:
                print("[!] Server manager reported an error.")

    except Exception as error:
        print(f"[!] Publishing/server error: {error}")

    successful = sum(bool(x) for x in downloaded.values())

    print("\n[+] Local HTML report created")
    print(f"[+] Results: {len(results)}")
    print(f"[+] Thumbnails downloaded: {successful}")
    print(f"[+] Thumbnails folder: {image_folder}")
    print(f"[+] HTML report: {output}")


if __name__ == "__main__":
    main()
