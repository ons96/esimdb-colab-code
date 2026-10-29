# esimdb-colab-code

A tiny, dependency-free **travel eSIM plan database** you can run locally or in
**Google Colab**. `esimdb` keeps eSIM data plans in a CSV file and answers
questions like *"cheapest plan for Japan with at least 10 GB"* by total price
and price-per-GB.

> **Status note (issue #1002):** this repo started as an empty placeholder —
> no description and none of the scaffold docs the issue expected. It was
> bootstrapped into a minimal working tool matching the repo name: an
> **eSIM** plan **db** with **Colab** support. It is a self-contained local
> database: it does not scrape esimdb.com or any provider site, and the
> bundled data is sample-only — replace it with your own.

## Requirements

- Python 3.9+
- No third-party packages (standard library only)

## Quickstart (local)

```bash
git clone https://github.com/ons96/esimdb-colab-code.git
cd esimdb-colab-code

python -m esimdb init        # seeds data/plans.csv from data/sample_plans.csv
python -m esimdb list        # show all plans
```

Search and rank:

```bash
python -m esimdb search --country Japan --min-data-gb 5
python -m esimdb best --country France          # lowest USD/GB first
python -m esimdb search --max-price-usd 15 --min-data-gb 5
```

Add a plan (writes back to the CSV):

```bash
python -m esimdb add --provider "NewSim" --country Spain \
    --data-gb 7 --validity-days 14 --price-usd 12.5 --notes "LTE"
```

Use `--db PATH` with any command to point at a different CSV file, and
`--force` with `init` to overwrite an existing one.

## Google Colab

Open [`notebooks/esimdb_demo.ipynb`](notebooks/esimdb_demo.ipynb) directly in
Colab (badge inside the notebook), then **Runtime → Run all**. The notebook
clones this repo and walks through `init`, `list`, `search`, `best`, and the
Python API.

## Python API

```python
from esimdb.db import EsimDatabase

db = EsimDatabase.load("data/plans.csv")
db.save("data/plans.csv")            # round-trips cleanly

plans = db.search(country="USA", max_price_usd=15.0)
best = db.best_value(country="Japan", min_data_gb=3)
print(db.to_table(best))             # fixed-width text table
```

## Data format

One CSV row per plan (`data/sample_plans.csv`):

| Column          | Type   | Notes                            |
|-----------------|--------|----------------------------------|
| `provider`      | string | e.g. `Airalo`                    |
| `country`       | string | e.g. `Japan` or `Global`         |
| `data_gb`       | number | gigabytes included (> 0)         |
| `validity_days` | int    | days the plan stays active (> 0) |
| `price_usd`     | number | total price in USD (>= 0)       |
| `notes`         | string | optional free text               |

## Testing

```bash
python -m unittest discover -s tests -v
```

CI runs the same suite on every push/PR via
[`.github/workflows/tests.yml`](.github/workflows/tests.yml) (plus the
existing gitleaks scan).

## Project layout

```
esimdb/            package: models.py, db.py, __main__.py (CLI)
data/              sample_plans.csv seed data (plans.csv is your local DB)
notebooks/         Colab demo notebook
tests/             unittest suite
```
