import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from PicImageSearch import (
    Network,
    Yandex,
    BaiDu,
    AnimeTrace,
    Iqdb,
    Tineye,
)


ENGINES = {
    "yandex": Yandex,
    "baidu": BaiDu,
    "animetrace": AnimeTrace,
    "iqdb": Iqdb,
    "tineye": Tineye,
}


def colour(code, text):
    if sys.stdout.isatty():
        return f"\033[{code}m{text}\033[0m"
    return text


def plain(value):
    """Convert values into JSON-safe Python data."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, dict):
        return {str(k): plain(v) for k, v in value.items()}

    if isinstance(value, (list, tuple)):
        return [plain(v) for v in value]

    return str(value)


def get_source(url):
    if not url:
        return ""

    try:
        host = urlparse(str(url)).hostname or ""
        return host.removeprefix("www.")
    except Exception:
        return ""


def extract_characters(item, origin):
    characters = getattr(item, "characters", None)

    if not characters and isinstance(origin, dict):
        characters = origin.get("character", [])

    output = []

    for character in characters or []:
        if isinstance(character, dict):
            name = character.get("character") or character.get("name", "")
            work = character.get("work", "")
        else:
            name = getattr(character, "name", "")
            work = getattr(character, "work", "")

        if name or work:
            output.append({
                "name": str(name),
                "work": str(work),
            })

    return output


def extract_result(item, engine):
    origin = getattr(item, "origin", {}) or {}

    if not isinstance(origin, dict):
        origin = {}

    original = origin.get("originalImage", {}) or {}

    if not isinstance(original, dict):
        original = {}

    url = getattr(item, "url", "") or origin.get("url", "")
    thumbnail = getattr(item, "thumbnail", "")

    title = (
        getattr(item, "title", "")
        or origin.get("title", "")
    )

    source = (
        getattr(item, "source", "")
        or origin.get("domain", "")
        or get_source(url)
    )

    description = (
        getattr(item, "content", "")
        or origin.get("description", "")
    )

    image_size = getattr(item, "size", "") or ""

    metadata = {}

    if engine == "baidu":
        width = origin.get("width")
        height = origin.get("height")

        if width and height:
            image_size = f"{width}x{height}"

        metadata = {
            "width": width,
            "height": height,
            "original_page": origin.get("fromUrl", ""),
        }

    elif engine == "animetrace":
        characters = extract_characters(item, origin)

        not_confident = getattr(item, "not_confident", None)
        if not_confident is None:
            not_confident = origin.get("not_confident")

        metadata = {
            "result_type": "character_candidates",
            "characters": characters,
            "box": plain(getattr(item, "box", None)),
            "box_id": getattr(item, "box_id", ""),
            "not_confident": not_confident,
        }

        if characters:
            title = (
                f"{characters[0]['name']} — "
                f"{characters[0]['work']}"
            )

            candidates = [
                f"{c['name']} ({c['work']})"
                for c in characters
            ]

            label = (
                "Character candidates (not confident): "
                if not_confident else "Character candidates: "
            )
            description = label + "; ".join(candidates)

        source = "AnimeTrace"

    elif engine == "iqdb":
        source = source or "IQDB"

    elif engine == "yandex":
        source = source or "Yandex"

    elif engine == "baidu":
        source = source or "Baidu"

    return {
        "engine": engine,
        "title": str(title or ""),
        "source": str(source or ""),
        "url": str(url or ""),
        "thumbnail": str(thumbnail or ""),
        "original_image": str(original.get("url", "") or ""),
        "description": str(description or ""),
        "image_size": str(image_size or ""),
        "similarity": getattr(item, "similarity", None),
        "metadata": metadata,
    }


async def search_one(name, engine_class, client, image_path):
    print(colour("36", f"\n[+] Starting {name.upper()}..."))

    try:
        engine = engine_class(client=client)
        response = await engine.search(file=image_path)

        raw_results = getattr(response, "raw", []) or []
        results = []

        for item in raw_results:
            result = extract_result(item, name)

            # Ignore empty placeholder records, especially IQDB's
            # "No relevant matches" response.
            if name == "iqdb":
                if not result["url"] and not result["thumbnail"]:
                    continue

            results.append(result)

        return {
            "engine": name,
            "status": "completed",
            "search_url": getattr(response, "url", "") or "",
            "results": results,
            "error": "",
        }

    except Exception as error:
        return {
            "engine": name,
            "status": "failed",
            "search_url": "",
            "results": [],
            "error": repr(error),
        }


async def search_image(image_path, selected, timeout):
    async with Network(timeout=timeout) as client:
        tasks = [
            search_one(name, ENGINES[name], client, image_path)
            for name in selected
        ]

        return await asyncio.gather(*tasks)


def main():
    parser = argparse.ArgumentParser(
        description="Multi-engine reverse image search for Termux."
    )

    parser.add_argument("image", help="Path to the image file")

    group = parser.add_mutually_exclusive_group()

    group.add_argument(
        "--all",
        action="store_true",
        help="Search using all five integrated engines"
    )

    group.add_argument(
        "--engine",
        help="Comma-separated engines: yandex,baidu,animetrace,iqdb,tineye"
    )

    parser.add_argument(
        "--list-engines",
        action="store_true",
        help="List integrated engines and exit"
    )

    parser.add_argument(
        "-n", "--limit",
        type=int,
        default=10,
        help="Number of results to display (default: 10)"
    )

    parser.add_argument(
        "-o", "--output",
        help="Save JSON report to a specified file"
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=90,
        help="Request timeout in seconds (default: 90)"
    )

    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Do not automatically save a report"
    )

    parser.add_argument(
        "--menu-child",
        action="store_true",
        help=argparse.SUPPRESS
    )

    if "--list-engines" in sys.argv:
        print("Integrated reverse image search engines:")
        for name in ENGINES:
            print(f"  - {name}")
        return 0

    args = parser.parse_args()

    if args.list_engines:
        print("Integrated reverse image search engines:")
        for name in ENGINES:
            print(f"  - {name}")
        return 0

    image_path = Path(args.image).expanduser().resolve()

    if not image_path.is_file():
        print(colour("31", f"Error: Image not found: {image_path}"))
        return 1

    if args.limit < 1:
        parser.error("--limit must be at least 1.")

    if not 5 <= args.timeout <= 300:
        parser.error("--timeout must be between 5 and 300 seconds.")

    if args.all:
        selected = list(ENGINES)

    elif args.engine:
        selected = [
            name.strip().lower()
            for name in args.engine.split(",")
            if name.strip()
        ]

        unknown = sorted(set(selected) - set(ENGINES))

        if unknown:
            parser.error(
                "Unknown engine(s): " + ", ".join(unknown)
            )

        # Remove duplicates while preserving order.
        selected = list(dict.fromkeys(selected))

        if not selected:
            parser.error("Select at least one engine.")

    else:
        selected = ["yandex"]

    print(colour("36", "\n[+] MULTI-ENGINE REVERSE IMAGE SEARCH"))
    print(f"[+] Image: {image_path}")
    print(f"[+] Engines: {', '.join(selected)}")
    print("[+] Mode: Concurrent")
    print("[+] Searching...\n")

    try:
        reports = asyncio.run(
            search_image(image_path, selected, args.timeout)
        )

    except Exception as error:
        print(colour("31", f"[!] Search session failed: {error!r}"))
        return 1

    all_results = []
    engine_stats = {}
    search_urls = {}

    for report in reports:
        name = report["engine"]
        results = report["results"]

        engine_stats[name] = {
            "status": report["status"],
            "total_results": len(results),
            "error": report["error"],
        }

        if report["search_url"]:
            search_urls[name] = report["search_url"]

        if report["status"] == "completed":
            print(
                colour(
                    "32",
                    f"[+] {name.upper()}: {len(results)} results"
                )
            )
        else:
            print(
                colour(
                    "31",
                    f"[!] {name.upper()} failed: {report['error']}"
                )
            )

        all_results.extend(results)

    print(colour("36", "\n[+] SEARCH SUMMARY"))
    print(f"[+] Engines completed: {sum(r['status'] == 'completed' for r in reports)}")
    print(f"[+] Engines failed: {sum(r['status'] == 'failed' for r in reports)}")
    print(f"[+] Total results: {len(all_results)}")

    for number, item in enumerate(all_results[:args.limit], 1):
        print("\n" + colour("36", f"========== RESULT {number} =========="))
        print(f"Engine: {item['engine'].upper()}")
        print(colour("33", f"Title: {item['title'] or 'N/A'}"))
        print(f"Website: {item['source'] or 'N/A'}")
        print(f"Image size: {item['image_size'] or 'N/A'}")
        print(f"Similarity: {item['similarity']}")
        print(f"Page URL: {item['url'] or 'N/A'}")
        print(f"Original image: {item['original_image'] or 'N/A'}")
        print(f"Thumbnail: {item['thumbnail'] or 'N/A'}")
        print(f"Description: {item['description'] or 'N/A'}")

    if not args.no_save:
        if args.output:
            output_path = Path(args.output).expanduser()
        else:
            report_dir = Path.home() / "reports" / "reverse-image"
            report_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            output_path = report_dir / f"report_{timestamp}.json"

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Preserve the original report fields for compatibility
        # with reverse_image_html.py and reverse_image_local.py.
        report_data = {
            "image": str(image_path),
            "engine": ", ".join(name.title() for name in selected),
            "search_url": (
                reports[0]["search_url"]
                if len(reports) == 1 else ""
            ),
            "search_urls": search_urls,
            "engines": engine_stats,
            "total_results": len(all_results),
            "results": all_results,
        }

        output_path.write_text(
            json.dumps(report_data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

        print(colour("32", f"\n[+] JSON report saved: {output_path}"))

        report_dir = Path.home() / "reports" / "reverse-image"


        if (
            not args.menu_child
            and sys.stdin.isatty()
            and output_path.resolve().parent == report_dir.resolve()
            and any(r["status"] == "completed" for r in reports)
        ):
            try:
                from reverse_image_menu import (
                    create_local_report,
                    interactive_menu,
                )

                print(colour("36", "\n[+] Preparing local HTML report..."))
                create_local_report(output_path)

                interactive_menu(
                    current_report=output_path,
                    image_path=image_path,
                    selected=selected,
                    limit=args.limit,
                    timeout=args.timeout,
                )

            except Exception as error:
                print(colour("31", f"[!] Interactive menu could not start: {error}"))

    print(colour("32", "\n[+] Done."))

    return 0 if any(r["status"] == "completed" for r in reports) else 1


if __name__ == "__main__":
    sys.exit(main())
