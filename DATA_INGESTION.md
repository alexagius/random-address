# Data Ingestion Workflow

This fork can be used directly by other projects while you expand the bundled
address dataset.

## Use This Fork In Another Project

For active local development from a consuming project's virtual environment:

```powershell
python -m pip install -e ..\random-address
```

Adjust `..\random-address` to the relative path from that project to this
checkout.

For a GitHub-pinned install:

```powershell
pip install "random-address @ git+https://github.com/alexagius/random-address.git@add-missing-state-data"
```

The import remains:

```python
import random_address
```

## Add Address Data

Put raw source files under `data/sources/`. That directory is intentionally
ignored by git, so large downloaded inputs do not end up in the package.

For a small first pass that gives missing states coverage from current
OpenAddresses data, use the sample importer:

```powershell
python data\import_openaddresses_samples.py
```

By default, it imports public samples from up to three OpenAddresses sources per
state that is not already represented in the packaged dataset. Records are only
kept when they include `address1`, `city`, `state`, `postalCode`, and
coordinates.

See `DATASET_COVERAGE.md` for per-state existing, added, and total record
counts.

For broader ZIP coverage, use the Overture Maps importer. It requires DuckDB in
the development virtual environment because it queries Overture's public
GeoParquet files directly:

```powershell
python -m pip install duckdb
python data\import_overture_samples.py --per-postal-code 5
```

This keeps up to five complete, geocoded addresses per state/ZIP pair when the
source provides them. Use `--per-postal-code 10` for a larger local fork.

The Netsyms address database can also be tested locally after downloading a
SQLite file from their site:

```powershell
python data\import_sqlite_addresses.py `
  --input data\sources\netsyms-addresses.sqlite `
  --per-postal-code 5 `
  --attribution "Netsyms Address Database"
```

Netsyms source files belong under `data/sources/`, which is ignored by git.
Review the source terms before redistributing any records imported from that
database.

New Hampshire is imported from NH GRANIT's public parcel point layer and
companion geocoder because the OpenAddresses and Overture sources checked for
this branch did not provide complete ZIP-coded NH records:

```powershell
python data\import_nh_granit_addresses.py --per-postal-code 10
```

The ingestion script accepts OpenAddresses-style CSV files, GeoJSON
FeatureCollections, and newline-delimited GeoJSON Features:

```powershell
python data\ingest_addresses.py `
  --input data\sources\ny-addresses.csv `
  --state NY `
  --attribution "Source Name (NY)" `
  --per-postal-code 5 `
  --limit 500
```

Useful options:

- `--dry-run`: print the incoming and merged counts without writing the package
  dataset.
- `--per-postal-code N`: keep up to `N` addresses per ZIP code.
- `--limit N`: cap the total incoming addresses after ZIP sampling.
- `--replace-state`: remove existing records for the state before adding new
  records.
- `--pretty`: write readable JSON when inspecting output. Leave this off for the
  minified package file.

After a successful merge, run tests:

```powershell
python -m pytest
```

If you use a project-local virtual environment, keep it in `.venv/`; that path
is ignored by git.

Then commit and push:

```powershell
git add data\ingest_addresses.py tests\test_ingest_addresses.py DATA_INGESTION.md random_address\addresses-us-all.min.json
git commit -m "Add address ingestion workflow"
git push
```
