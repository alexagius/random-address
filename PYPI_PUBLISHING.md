# PyPI Publishing

This fork publishes under the PyPI distribution name
`random-address-extended`. The Python import remains:

```python
import random_address
```

## Trusted Publisher Setup

Configure trusted publishing on both TestPyPI and PyPI before running the
publish workflow.

Use these values:

| Field | Value |
| --- | --- |
| PyPI project | `random-address-extended` |
| GitHub owner | `alexagius` |
| GitHub repository | `random-address` |
| Workflow filename | `publish.yml` |
| TestPyPI environment | `testpypi` |
| PyPI environment | `pypi` |

Trusted publishing uses GitHub OIDC, so no PyPI API token needs to be stored in
this repository.

## TestPyPI

After the trusted publisher is configured on TestPyPI:

1. Open the `Publish Python Package` GitHub Actions workflow.
2. Choose `Run workflow`.
3. Set `target` to `testpypi`.

The package should publish to:

```text
https://test.pypi.org/project/random-address-extended/
```

## PyPI

After the trusted publisher is configured on PyPI, publish to the real index by
creating a GitHub Release from a tag that points at a commit containing
`.github/workflows/publish.yml`.

The package should publish to:

```text
https://pypi.org/project/random-address-extended/
```

Manual PyPI publishing is also available from the workflow dispatch screen by
setting `target` to `pypi`, but a GitHub Release is the preferred path for real
PyPI releases.

## Local Verification

```powershell
python -m pip install build twine
python -m build
python -m twine check dist/*
```
