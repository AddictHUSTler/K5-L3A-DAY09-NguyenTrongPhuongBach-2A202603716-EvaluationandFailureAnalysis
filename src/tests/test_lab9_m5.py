"""M5: slice regressions, item pairing and v2 coverage."""
import copy
from collections import Counter
from pathlib import Path

import pytest
import yaml

from lab9 import evalset, gate

pytestmark = pytest.mark.student


def reports():
    rows = [
        {"item_id": str(i), "seed": seed, "pass_rate": True,
         "slices": ["small_slice"] if i < 3 else []}
        for i in range(30) for seed in (11, 22, 33, 44, 55)
    ]
    base = {"rows": rows}
    return copy.deepcopy(base), base


def spec(**overrides):
    return {"slices": [{"name": "small_slice", "metric": "pass_rate",
                        "min": 0.9, "no_significant_drop": True,
                        "blocking": True, **overrides}]}


def test_small_slice_blocks_when_overall_mean_hides_regression():
    pr, base = reports()
    for row in pr["rows"]:
        if row["item_id"] == "0":
            row["pass_rate"] = False
    assert sum(r["pass_rate"] for r in pr["rows"]) / len(pr["rows"]) > 0.85
    blocked, lines = gate.slice_check(pr, base, spec())
    assert blocked == ["slice:small_slice/pass_rate"]
    assert "CI" in lines[0] and "BLOCK" in lines[0]


def test_slice_ci_blocks_above_floor_and_pairs_by_item():
    pr, base = reports()
    for row in pr["rows"]:
        if row["slices"] and row["seed"] == 11:
            row["pass_rate"] = False
    pr["rows"].reverse()
    assert gate.slice_check(pr, base, spec(min=0.7))[0] == ["slice:small_slice/pass_rate"]


def test_identical_slice_merges_and_nonblocking_failure_only_warns():
    pr, base = reports()
    assert gate.slice_check(pr, base, spec())[0] == []
    for row in pr["rows"]:
        row["pass_rate"] = False
    blocked, lines = gate.slice_check(pr, base, spec(blocking=False))
    assert blocked == []
    assert "warn" in lines[0]


def test_missing_slice_items_block_without_bootstrap_crash():
    pr, base = reports()
    pr["rows"] = [r for r in pr["rows"] if not r["slices"]]
    assert gate.slice_check(pr, base, spec())[0] == ["slice:small_slice/pass_rate"]


def test_v2_mechanisms_and_coverage():
    root = Path(__file__).resolve().parents[1]
    items = evalset.load_jsonl(root / evalset.ITEMS_V2)
    mapping = yaml.safe_load((root / evalset.FM_MAP).read_text())
    import json
    pack = json.loads((root / evalset.PACK).read_text())
    by_claim = {item["claim_id"]: item for item in items}
    counts = Counter(fm for item in items for fm in set(item["failure_modes"]))
    for claim in pack["claims"]:
        item = by_claim[claim["claim_id"]]
        assert item["failure_modes"] == [mapping[m] for m in claim["mechanisms"]]
        assert all(counts[fm] >= 3 for fm in item["failure_modes"])
        assert "adversarial" in item["slices"]
    assert all("expected" not in item and "label" not in item for item in items)
