import gzip
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

with open("addresses-us-all.json", "r", encoding="utf-8") as file:
    data = json.load(file)

with gzip.open(ROOT / "random_address" / "addresses-us-all.min.json.gz", "wt", encoding="utf-8") as file:
    json.dump(data, file, separators=(",", ":"))
