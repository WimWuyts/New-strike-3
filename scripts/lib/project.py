"""Projectpaden, configuratie en hervatbare state.

Alle scripts lezen hun instellingen hier vandaan. Niets in de pipeline mag
waarden hardcoderen die in config/project.yaml staan.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]

CONFIG_PATH = ROOT / "config" / "project.yaml"
SCHEMA_DIR = ROOT / "schemas"
SOURCES_DIR = ROOT / "sources"
DATA_DIR = ROOT / "data"
EXTRACTED_DIR = DATA_DIR / "extracted"
CATALOG_DIR = DATA_DIR / "catalog"
CONTENT_DIR = DATA_DIR / "content"
SOURCE_MAP_DIR = DATA_DIR / "source-maps"
ASSETS_DIR = ROOT / "assets"
STATE_DIR = ROOT / "state"
REPORTS_DIR = ROOT / "reports"
BUILD_DIR = ROOT / "build"
DIST_DIR = ROOT / "dist"

PROGRESS_PATH = STATE_DIR / "progress.json"
HASHES_PATH = STATE_DIR / "content-hashes.json"


class ProjectError(RuntimeError):
    """Fout die de gebruiker moet oplossen voordat de pipeline verder kan."""


# ---------------------------------------------------------------------------
# Configuratie
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BookConfig:
    id: str
    title: str
    edition: str | None
    unit_count: int
    cefr_target: str
    audience: str
    themes: list[dict[str, Any]]

    @property
    def source_dir(self) -> Path:
        return SOURCES_DIR / "books" / self.id

    def theme_ids(self) -> list[str]:
        return [t["id"] for t in self.themes]

    @property
    def available_themes(self) -> list[dict[str, Any]]:
        """Thema's waarvan de bron-pdf aangeleverd is.

        Een thema kan bestaan in het boek zonder dat de pdf er is. Zo'n thema
        blijft in de kaart staan, maar mag de extractie niet blokkeren.
        """
        return [t for t in self.themes if t.get("source_available", True)]

    @property
    def unavailable_themes(self) -> list[dict[str, Any]]:
        return [t for t in self.themes if not t.get("source_available", True)]

    def theme(self, theme_id: str) -> dict[str, Any]:
        for entry in self.themes:
            if entry["id"] == theme_id:
                return entry
        raise ProjectError(
            f"Thema {theme_id!r} bestaat niet in boek {self.id!r}. "
            f"Bekend: {', '.join(self.theme_ids())}"
        )


class Config:
    """Gelezen weergave van config/project.yaml."""

    def __init__(self, raw: dict[str, Any]) -> None:
        self._raw = raw

    @classmethod
    def load(cls, path: Path = CONFIG_PATH) -> "Config":
        if not path.exists():
            raise ProjectError(f"Configuratie ontbreekt: {path}")
        with path.open(encoding="utf-8") as handle:
            return cls(yaml.safe_load(handle))

    def __getitem__(self, key: str) -> Any:
        return self._raw[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self._raw.get(key, default)

    # -- boeken ------------------------------------------------------------

    @property
    def books(self) -> list[BookConfig]:
        return [
            BookConfig(
                id=entry["id"],
                title=entry["title"],
                edition=entry.get("edition"),
                unit_count=entry["unit_count"],
                cefr_target=entry["cefr_target"],
                audience=entry["audience"],
                themes=entry["themes"],
            )
            for entry in self._raw["books"]
        ]

    def book(self, book_id: str) -> BookConfig:
        for book in self.books:
            if book.id == book_id:
                return book
        known = ", ".join(b.id for b in self.books)
        raise ProjectError(f"Onbekend boek {book_id!r}. Bekend: {known}")

    def book_for_theme(self, theme_id: str) -> BookConfig:
        for book in self.books:
            if theme_id in book.theme_ids():
                return book
        raise ProjectError(f"Thema {theme_id!r} hoort bij geen enkel boek.")

    # -- veelgebruikte secties --------------------------------------------

    @property
    def extraction(self) -> dict[str, Any]:
        return self._raw["extraction"]

    @property
    def exercises(self) -> dict[str, Any]:
        return self._raw["exercises"]

    @property
    def rights(self) -> dict[str, Any]:
        return self._raw["rights"]

    @property
    def pptx(self) -> dict[str, Any]:
        return self._raw["pptx"]

    @property
    def modules(self) -> dict[str, Any]:
        return self._raw["modules"]

    # -- rechten -----------------------------------------------------------

    def _assert_confirmation_on_file(self) -> Path:
        confirmation = ROOT / self.rights["confirmation_file"]
        if not self.rights.get("confirmed") or not confirmation.exists():
            raise ProjectError(
                "Er is geen geldige rechtenbevestiging.\n"
                f"  rights.confirmed = {self.rights.get('confirmed')}\n"
                f"  bevestigingsbestand aanwezig = {confirmation.exists()} ({confirmation})"
            )
        return confirmation

    def assert_may_reproduce_pages(self) -> None:
        """Bewaakt de poort rond paginagetrouwe reproductie.

        Deze poort hangt aan een eigen vlag en niet alleen aan `confirmed`.
        Een bevestiging voor antwoordsleutels mag hier niet doorheen lekken:
        dat zijn twee verschillende toestemmingen.
        """
        self._assert_confirmation_on_file()
        if not self.rights.get("allow_page_faithful_reproduction"):
            raise ProjectError(
                "Paginagetrouwe reproductie is geblokkeerd.\n"
                "  rights.allow_page_faithful_reproduction = false\n"
                "Een bevestiging voor antwoordsleutels dekt dit niet. Gebruik de "
                "modus hybrid_classroom_16x9, of leg een aparte bevestiging vast."
            )

    def assert_may_use_source_answer_keys(self) -> str:
        """Bewaakt de poort rond de antwoordsleutels van het boek.

        Geeft het bevestigde gebruiksbereik terug, zodat de bouwstap dat op het
        artefact kan zetten.
        """
        self._assert_confirmation_on_file()
        if not self.rights.get("allow_source_answer_keys"):
            raise ProjectError(
                "Verwerken van antwoordsleutels uit de bron is geblokkeerd.\n"
                "  rights.allow_source_answer_keys = false"
            )
        scope = self.rights.get("use_scope")
        if not scope:
            raise ProjectError(
                "rights.use_scope ontbreekt. Leg vast hoe ver het materiaal mag "
                "reizen voordat er broninhoud verwerkt wordt."
            )
        return str(scope)


# ---------------------------------------------------------------------------
# Hashing en hervatbaarheid
# ---------------------------------------------------------------------------


def file_sha256(path: Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def content_hash(payload: Any) -> str:
    """Stabiele hash van een JSON-serialiseerbare structuur.

    Het veld content_hash zelf wordt genegeerd, zodat de hash van een object
    niet van zichzelf afhangt.
    """
    normalised = _strip_hash_fields(payload)
    encoded = json.dumps(normalised, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _strip_hash_fields(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _strip_hash_fields(v) for k, v in value.items() if k != "content_hash"}
    if isinstance(value, list):
        return [_strip_hash_fields(v) for v in value]
    return value


def write_json_atomic(path: Path, payload: Any) -> None:
    """Schrijft JSON atomair, zodat een onderbroken run niets half achterlaat."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False, suffix=".tmp"
    )
    try:
        with handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(handle.name, path)
    except BaseException:
        Path(handle.name).unlink(missing_ok=True)
        raise


def read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


class State:
    """Voortgang en contenthashes, voor idempotente en hervatbare runs."""

    def __init__(self) -> None:
        self.progress: dict[str, Any] = read_json(PROGRESS_PATH, default=None) or {
            "schema_version": "v1",
            "stages": {},
            "themes": {},
        }
        self.hashes: dict[str, str] = read_json(HASHES_PATH, default=None) or {}

    def is_current(self, key: str, digest: str) -> bool:
        """True als dit artefact al gebouwd is met exact deze invoer."""
        if os.environ.get("FORCE"):
            return False
        return self.hashes.get(key) == digest

    def mark(self, key: str, digest: str) -> None:
        self.hashes[key] = digest

    def set_stage(self, stage: str, status: str, **details: Any) -> None:
        self.progress.setdefault("stages", {})[stage] = {"status": status, **details}

    def set_theme(self, theme_id: str, **details: Any) -> None:
        entry = self.progress.setdefault("themes", {}).setdefault(theme_id, {})
        entry.update(details)

    def save(self) -> None:
        write_json_atomic(PROGRESS_PATH, self.progress)
        write_json_atomic(HASHES_PATH, self.hashes)


def ensure_dirs(*paths: Path) -> None:
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)


def relative(path: Path) -> str:
    """Pad relatief aan de projectroot, voor leesbare rapporten."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)
