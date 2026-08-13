#!/usr/bin/env python3
"""Bundelt de webbuild tot één zelfstandig HTML-bestand.

`vite build` levert een index.html met losse js- en css-bestanden. Voor een
leerkracht is dat lastig: je kunt het niet doorsturen en niet zomaar op een
leerplatform zetten. Dit script giet alles in één bestand dat je kunt openen
met een dubbelklik, zonder webserver en zonder netwerk.

Werkt alleen omdat de content bij het bouwen al in de bundel zit; er wordt
niets opgehaald tijdens het openen.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.project import DIST_DIR, ROOT, relative  # noqa: E402

SCRIPT_TAG = re.compile(
    r'<script[^>]*\ssrc="(?P<src>[^"]+)"[^>]*>\s*</script>', re.IGNORECASE
)
STYLE_TAG = re.compile(
    r'<link[^>]*\srel="stylesheet"[^>]*\shref="(?P<href>[^"]+)"[^>]*>', re.IGNORECASE
)


def _read_asset(build_dir: Path, reference: str) -> str:
    path = (build_dir / reference.lstrip("./")).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Verwezen bestand ontbreekt: {reference}")
    return path.read_text(encoding="utf-8")


def bundle(build_dir: Path, out_path: Path) -> tuple[int, int]:
    index = build_dir / "index.html"
    if not index.exists():
        raise FileNotFoundError(
            f"Geen webbuild in {relative(build_dir)}. Draai eerst: npm run build:web"
        )

    html = index.read_text(encoding="utf-8")
    inlined_scripts = 0
    inlined_styles = 0

    def replace_script(match: re.Match[str]) -> str:
        nonlocal inlined_scripts
        code = _read_asset(build_dir, match.group("src"))
        inlined_scripts += 1
        # </script> in de code zelf zou de tag vroegtijdig sluiten.
        safe = code.replace("</script>", "<\\/script>")
        return f'<script type="module">{safe}</script>'

    def replace_style(match: re.Match[str]) -> str:
        nonlocal inlined_styles
        css = _read_asset(build_dir, match.group("href"))
        inlined_styles += 1
        return f"<style>{css}</style>"

    html = STYLE_TAG.sub(replace_style, html)
    html = SCRIPT_TAG.sub(replace_script, html)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return inlined_scripts, inlined_styles


def main() -> int:
    parser = argparse.ArgumentParser(description="Bundel de webbuild tot één HTML-bestand.")
    parser.add_argument("--build-dir", default=str(DIST_DIR / "web"))
    parser.add_argument("--out", help="Standaard dist/web/oefenomgeving.html")
    args = parser.parse_args()

    build_dir = Path(args.build_dir)
    out_path = Path(args.out) if args.out else DIST_DIR / "web" / "oefenomgeving.html"

    scripts, styles = bundle(build_dir, out_path)
    size_kb = out_path.stat().st_size / 1024

    print(f"Gebouwd: {relative(out_path)}")
    print(f"Ingesloten: {scripts} script(s), {styles} stylesheet(s)")
    print(f"Grootte: {size_kb:.0f} kB")
    if size_kb > 8000:
        print("Let op: dit bestand wordt groot. Overweeg per thema te exporteren.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, OSError) as exc:
        print(f"Fout: {exc}", file=sys.stderr)
        raise SystemExit(2)
