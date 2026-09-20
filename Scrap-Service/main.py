"""
Scrap Service - Orchestrator
=============================

Walks through the `scrapers/` folder, runs each scraper, collects
exchange rates from every house, and persists them to the repository.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable

# Adjust this import to match your actual repository location
from scrap_service.repository import CurrencyRepository


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# Currencies we care about. If a scraper returns more, they're ignored;
# if it returns fewer, they're simply skipped.
TARGET_CURRENCIES: tuple[str, ...] = ("USD", "EUR")

# Name of the function every scraper must expose.
SCRAPER_ENTRYPOINT = "get_cotization"


@dataclass
class Paths:
    """Project paths, resolved once."""

    file: Path
    base: Path
    data: Path
    scrapers: Path

    @classmethod
    def resolve(cls, file: str | Path = __file__) -> "Paths":
        current = Path(file).resolve()
        base = current.parent.parent
        return cls(
            file=current,
            base=base,
            data=base / "data" / "market-rates.json",
            scrapers=base / "scrapers",
        )


@dataclass
class ScrapeResult:
    """Result of running a single scraper."""

    house: str
    currencies: dict[str, Any] = field(default_factory=dict)
    error: Exception | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and bool(self.currencies)


# ---------------------------------------------------------------------------
# Dynamic scraper loading
# ---------------------------------------------------------------------------

def iter_scraper_files(directory: Path) -> Iterable[Path]:
    """Yield every .py file inside scrapers/, skipping __init__.py and _*.py."""
    if not directory.is_dir():
        raise FileNotFoundError(f"Scrapers directory not found: {directory}")

    for path in sorted(directory.glob("*.py")):
        if path.name.startswith("_"):  # __init__.py, __pycache__, _helpers.py
            continue
        yield path


def load_module(path: Path) -> ModuleType:
    """
    Load a Python module from a file, registering it in sys.modules
    so that relative imports inside the scraper work correctly.
    """
    module_name = f"scrap_service.scrapers.{path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, path)

    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load spec for {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module  # key for relative imports
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Scraper execution
# ---------------------------------------------------------------------------

def run_scraper(path: Path) -> ScrapeResult:
    """Run a scraper and return the result, catching any errors."""
    house = path.stem

    try:
        module = load_module(path)
    except Exception as exc:
        logger.exception("Failed to import scraper %s", house)
        return ScrapeResult(house=house, error=exc)

    if not hasattr(module, SCRAPER_ENTRYPOINT):
        msg = f"Scraper '{house}' has no '{SCRAPER_ENTRYPOINT}()' function"
        logger.warning(msg)
        return ScrapeResult(house=house, error=RuntimeError(msg))

    try:
        raw = getattr(module, SCRAPER_ENTRYPOINT)()
    except Exception as exc:
        logger.exception("Scraper %s raised during execution", house)
        return ScrapeResult(house=house, error=exc)

    if not raw:
        logger.warning("Scraper %s returned empty data", house)
        return ScrapeResult(house=house, currencies={})

    # Keep only the currencies we care about
    filtered = {code: raw[code] for code in TARGET_CURRENCIES if code in raw}

    missing = set(TARGET_CURRENCIES) - filtered.keys()
    if missing:
        logger.debug("Scraper %s missing currencies: %s", house, missing)

    return ScrapeResult(house=house, currencies=filtered)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------

def persist(results: Iterable[ScrapeResult], repository: CurrencyRepository) -> int:
    """Save every rate to the repository. Returns how many were saved."""
    saved = 0

    for result in results:
        if not result.ok:
            continue

        for code, value in result.currencies.items():
            try:
                repository.save(value)
                saved += 1
                logger.debug("Saved %s from %s", code, result.house)
            except Exception:
                logger.exception(
                    "Failed to save %s from %s", code, result.house
                )

    return saved


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def update_data(repository: CurrencyRepository | None = None) -> dict[str, ScrapeResult]:
    """
    Orchestrates the whole pipeline:
      1. Walk through scrapers/
      2. Run each one
      3. Persist the results

    Returns a dict {house_name: ScrapeResult} for inspection/testing.
    """
    paths = Paths.resolve()
    repo = repository or CurrencyRepository()

    logger.info("Scanning scrapers in %s", paths.scrapers)

    results: dict[str, ScrapeResult] = {}

    for scraper_file in iter_scraper_files(paths.scrapers):
        result = run_scraper(scraper_file)
        results[result.house] = result

    saved = persist(results.values(), repo)
    logger.info("Pipeline finished: %d currencies saved", saved)

    return results


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    update_data()