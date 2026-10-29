import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from esimdb.db import EsimDatabase
from esimdb.models import Plan

REPO_ROOT = Path(__file__).resolve().parents[1]


def make_plan(**overrides):
    defaults = {
        "provider": "TestSim",
        "country": "France",
        "data_gb": 5,
        "validity_days": 30,
        "price_usd": 10.0,
    }
    defaults.update(overrides)
    return Plan(**defaults)


class PlanTests(unittest.TestCase):
    def test_valid_plan(self):
        plan = make_plan(data_gb=10, price_usd=25)
        self.assertEqual(plan.price_per_gb, 2.5)

    def test_coerces_strings(self):
        plan = make_plan(data_gb="5", validity_days="30", price_usd="10")
        self.assertEqual(plan.data_gb, 5.0)
        self.assertEqual(plan.validity_days, 30)

    def test_rejects_empty_fields(self):
        with self.assertRaises(ValueError):
            make_plan(provider=" ")
        with self.assertRaises(ValueError):
            make_plan(country="")

    def test_rejects_bad_numbers(self):
        with self.assertRaises(ValueError):
            make_plan(data_gb=0)
        with self.assertRaises(ValueError):
            make_plan(validity_days=-3)
        with self.assertRaises(ValueError):
            make_plan(price_usd=-1)


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "plans.csv"
        self.db = EsimDatabase(
            [
                make_plan(provider="A", country="Japan", data_gb=10, price_usd=20),
                make_plan(provider="B", country="Japan", data_gb=5, price_usd=6),
                make_plan(provider="C", country="France", data_gb=1, price_usd=4.5),
            ]
        )
        self.db.save(self.path)

    def test_missing_file_loads_empty(self):
        empty = EsimDatabase.load(Path(self.tmp.name) / "nope.csv")
        self.assertEqual(empty.plans, [])

    def test_roundtrip(self):
        loaded = EsimDatabase.load(self.path)
        self.assertEqual(len(loaded.plans), 3)
        self.assertEqual(loaded.plans[0].provider, "A")
        self.assertEqual(loaded.plans[0].data_gb, 10)
        self.assertEqual(loaded.plans[2].price_usd, 4.5)
        self.assertEqual(loaded.plans[0].notes, "")

    def test_bad_header_raises(self):
        bad = Path(self.tmp.name) / "bad.csv"
        bad.write_text("a,b,c\n1,2,3\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            EsimDatabase.load(bad)

    def test_search_filters(self):
        japan = self.db.search(country="japan")
        self.assertEqual({p.provider for p in japan}, {"A", "B"})
        big = self.db.search(country="Japan", min_data_gb=6)
        self.assertEqual([p.provider for p in big], ["A"])
        cheap = self.db.search(country="Japan", max_price_usd=7)
        self.assertEqual([p.provider for p in cheap], ["B"])
        by_provider = self.db.search(provider="c")
        self.assertEqual([p.country for p in by_provider], ["France"])

    def test_best_value_orders_by_price_per_gb(self):
        best = self.db.best_value(country="Japan")
        self.assertEqual([p.provider for p in best], ["B", "A"])
        self.assertEqual(best[0].price_per_gb, 1.2)

    def test_add_and_persist(self):
        self.db.add(make_plan(provider="D", country="Spain"))
        self.db.save(self.path)
        self.assertEqual(len(EsimDatabase.load(self.path).plans), 4)

    def test_table_renders_rows(self):
        table = self.db.to_table(self.db.search(country="France"))
        self.assertIn("PROVIDER", table)
        self.assertIn("France", table)

    def test_sample_data_loads(self):
        sample = EsimDatabase.load(REPO_ROOT / "data" / "sample_plans.csv")
        self.assertGreater(len(sample.plans), 0)
        self.assertGreater(sample.best_value(limit=1)[0].price_per_gb, 0)


class CliTests(unittest.TestCase):
    def run_cli(self, *args, cwd):
        env = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}
        return subprocess.run(
            [sys.executable, "-m", "esimdb", *args],
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
        )

    def test_happy_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            init = self.run_cli("init", cwd=tmp)
            self.assertEqual(init.returncode, 0, init.stderr)
            self.assertTrue((Path(tmp) / "data" / "plans.csv").exists())

            listing = self.run_cli("list", cwd=tmp)
            self.assertEqual(listing.returncode, 0, listing.stderr)
            self.assertIn("Airalo", listing.stdout)

            search = self.run_cli("search", "--country", "Japan", "--min-data-gb", "5", cwd=tmp)
            self.assertEqual(search.returncode, 0, search.stderr)
            self.assertIn("Japan", search.stdout)
            self.assertNotIn("France", search.stdout)

            best = self.run_cli("best", "--country", "France", cwd=tmp)
            self.assertEqual(best.returncode, 0, best.stderr)
            self.assertIn("USD/GB", best.stdout)

            add = self.run_cli(
                "add",
                "--provider", "NewSim",
                "--country", "Spain",
                "--data-gb", "7",
                "--validity-days", "14",
                "--price-usd", "12.5",
                cwd=tmp,
            )
            self.assertEqual(add.returncode, 0, add.stderr)
            self.assertIn("NewSim", add.stdout)

            verify = self.run_cli("search", "--provider", "NewSim", cwd=tmp)
            self.assertIn("NewSim", verify.stdout)

    def test_missing_db_hints_at_init(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli("list", cwd=tmp)
            self.assertEqual(result.returncode, 1)
            self.assertIn("init", result.stdout)

    def test_init_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = self.run_cli("init", cwd=tmp)
            self.assertEqual(first.returncode, 0, first.stderr)
            second = self.run_cli("init", cwd=tmp)
            self.assertEqual(second.returncode, 1)
            forced = self.run_cli("init", "--force", cwd=tmp)
            self.assertEqual(forced.returncode, 0, forced.stderr)

    def test_add_rejects_invalid_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(self.run_cli("init", cwd=tmp).returncode, 0)
            bad = self.run_cli(
                "add",
                "--provider", "X",
                "--country", "Y",
                "--data-gb", "0",
                "--validity-days", "7",
                "--price-usd", "5",
                cwd=tmp,
            )
            self.assertNotEqual(bad.returncode, 0)


if __name__ == "__main__":
    unittest.main()
