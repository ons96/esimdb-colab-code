"""Command-line interface: python -m esimdb <command>."""

import argparse
import shutil
import sys
from pathlib import Path

from .db import EsimDatabase
from .models import Plan

DEFAULT_DB = Path("data/plans.csv")
SAMPLE_DB = Path(__file__).resolve().parent.parent / "data" / "sample_plans.csv"


def build_parser():
    parser = argparse.ArgumentParser(
        prog="esimdb",
        description="Local travel eSIM plan database (CSV-backed, no dependencies)",
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB, help="plan CSV file path")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="seed the database file with sample plans")
    init.add_argument("--force", action="store_true", help="overwrite an existing file")

    sub.add_parser("list", help="show all plans")

    search = sub.add_parser("search", help="filter plans")
    search.add_argument("--country")
    search.add_argument("--provider")
    search.add_argument("--min-data-gb", type=float)
    search.add_argument("--max-price-usd", type=float)

    best = sub.add_parser("best", help="rank plans by lowest price per GB")
    best.add_argument("--country")
    best.add_argument("--min-data-gb", type=float)
    best.add_argument("--limit", type=int, default=5)

    add = sub.add_parser("add", help="add a plan and save the database")
    add.add_argument("--provider", required=True)
    add.add_argument("--country", required=True)
    add.add_argument("--data-gb", type=float, required=True)
    add.add_argument("--validity-days", type=int, required=True)
    add.add_argument("--price-usd", type=float, required=True)
    add.add_argument("--notes", default="")
    return parser


def load_or_hint(path):
    if not Path(path).exists():
        print(f"No database at {path}. Run: python -m esimdb init")
        return None
    return EsimDatabase.load(path)


def show(db, plans, empty_message="No plans found."):
    if not plans:
        print(empty_message)
        return 1
    print(db.to_table(plans))
    return 0


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.command == "init":
        if not SAMPLE_DB.exists():
            print(f"Sample data missing: {SAMPLE_DB}", file=sys.stderr)
            return 1
        if args.db.exists() and not args.force:
            print(f"{args.db} already exists (use --force to overwrite)")
            return 1
        args.db.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SAMPLE_DB, args.db)
        print(f"Seeded {args.db} with sample plans")
        return 0

    if args.command == "list":
        db = load_or_hint(args.db)
        if db is None:
            return 1
        return show(db, db.plans)

    if args.command == "search":
        db = load_or_hint(args.db)
        if db is None:
            return 1
        plans = db.search(
            country=args.country,
            provider=args.provider,
            min_data_gb=args.min_data_gb,
            max_price_usd=args.max_price_usd,
        )
        return show(db, plans)

    if args.command == "best":
        db = load_or_hint(args.db)
        if db is None:
            return 1
        plans = db.best_value(country=args.country, min_data_gb=args.min_data_gb, limit=args.limit)
        return show(db, plans, "No plans matched the filters.")

    if args.command == "add":
        db = EsimDatabase.load(args.db)
        db.add(
            Plan(
                provider=args.provider,
                country=args.country,
                data_gb=args.data_gb,
                validity_days=args.validity_days,
                price_usd=args.price_usd,
                notes=args.notes,
            )
        )
        db.save(args.db)
        print(f"Added and saved to {args.db}:")
        print(db.to_table(db.plans[-1:]))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
