# Data Ingestion Workflow

This fork can be used directly by other projects while you expand the bundled
address dataset.

## Use This Fork In Another Project

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

Then commit and push:

```powershell
git add data\ingest_addresses.py tests\test_ingest_addresses.py DATA_INGESTION.md random_address\addresses-us-all.min.json
git commit -m "Add address ingestion workflow"
git push
```
