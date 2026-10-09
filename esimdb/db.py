"""CSV-backed database of eSIM plans with search and ranking."""

import csv
from pathlib import Path

from .models import FIELDS, Plan

REQUIRED_COLUMNS = FIELDS[:5]


class EsimDatabase:
    """An in-memory collection of plans that persists to a CSV file."""

    def __init__(self, plans=None):
        self.plans = list(plans or [])

    @classmethod
    def load(cls, path):
        """Load plans from a CSV file; a missing file yields an empty database."""
        p = Path(path)
        if not p.exists():
            return cls()
        with p.open(newline="", encoding="utf-8") as f:
            rows = csv.DictReader(f)
            missing = [c for c in REQUIRED_COLUMNS if c not in (rows.fieldnames or [])]
            if missing:
                raise ValueError(f"missing columns in {path}: {', '.join(missing)}")
            return cls(Plan.from_row(row) for row in rows)

    def save(self, path):
        """Write all plans to a CSV file, creating parent directories."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(FIELDS))
            writer.writeheader()
            for plan in self.plans:
                writer.writerow(plan.to_row())

    def add(self, plan):
        """Append a plan to the database (call save() to persist)."""
        self.plans.append(plan)

    def search(self, country=None, provider=None, min_data_gb=None, max_price_usd=None):
        """Return plans matching all given filters (case-insensitive names)."""
        result = self.plans
        if country:
            needle = country.strip().lower()
            result = [p for p in result if p.country.strip().lower() == needle]
        if provider:
            needle = provider.strip().lower()
            result = [p for p in result if p.provider.strip().lower() == needle]
        if min_data_gb is not None:
            result = [p for p in result if p.data_gb >= min_data_gb]
        if max_price_usd is not None:
            result = [p for p in result if p.price_usd <= max_price_usd]
        return result

    def best_value(self, country=None, min_data_gb=None, limit=5):
        """Return up to limit plans with the lowest price per GB."""
        matches = self.search(country=country, min_data_gb=min_data_gb)
        return sorted(matches, key=lambda p: p.price_per_gb)[:limit]

    def to_table(self, plans=None):
        """Render plans (default: all) as a fixed-width text table."""
        rows = list(self.plans if plans is None else plans)
        header = ["PROVIDER", "COUNTRY", "GB", "DAYS", "USD", "USD/GB"]
        cells = [
            [
                p.provider,
                p.country,
                f"{p.data_gb:g}",
                str(p.validity_days),
                f"{p.price_usd:.2f}",
                f"{p.price_per_gb:.2f}",
            ]
            for p in rows
        ]
        widths = [len(h) for h in header]
        for row in cells:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(cell))
        lines = [
            "  ".join(h.ljust(w) for h, w in zip(header, widths)),
            "  ".join("-" * w for w in widths),
        ]
        lines.extend("  ".join(c.ljust(w) for c, w in zip(row, widths)) for row in cells)
        return "\n".join(lines)
