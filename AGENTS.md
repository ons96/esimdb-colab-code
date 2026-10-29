# AGENTS.md

Conventions for autonomous coding agents working in this repo.

- Python 3.9+, standard library only — code must run on Google Colab and free
  GitHub-hosted CI without installing anything.
- Package code lives in `esimdb/`; user-editable CSV data lives in `data/`
  (`sample_plans.csv` is the seed; `plans.csv` is the runtime database and is
  gitignored).
- CLI entry point is `python -m esimdb` (argparse subcommands).
- Tests use `unittest` and must pass before finishing any task:
  `python -m unittest discover -s tests`.
- Keep the implementation minimal; prefer small diffs over refactors unless
  the task explicitly asks for more.
