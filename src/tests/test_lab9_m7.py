"""M7: reject altered evidence and weaker specs before comparing scores."""
import copy
import json
from pathlib import Path

import pytest

from lab9 import gate, traps
from lab9.eval import load_spec

pytestmark = pytest.mark.student
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def inputs():
    spec = load_spec(ROOT / "config/metric_spec_v2.yaml")
    base = json.loads((ROOT / "reports/baseline_v2.json").read_text())
    return base, spec


@pytest.mark.parametrize("change", [
    "duplicate", "drop", "seed", "item", "manifest", "slice", "inconsistent_slice",
    "nan", "inf", "missing_score", "null_score", "row_nan", "string_score", "errors",
])
def test_altered_evidence_is_integrity_failure(inputs, change):
    base, spec = inputs
    pr = copy.deepcopy(base)
    row = pr["rows"][0]
    if change == "duplicate":
        pr["rows"][-1] = copy.deepcopy(row)  # Same count, different coverage.
    elif change == "drop":
        pr["rows"].pop()
    elif change == "seed":
        old = pr["manifest"]["seeds"][0]
        pr["manifest"]["seeds"][0] = 12345
        for r in pr["rows"]:
            if r["seed"] == old:
                r["seed"] = 12345
    elif change == "item":
        for r in pr["rows"]:
            if r["item_id"] == row["item_id"]:
                r["item_id"] = "substituted"
    elif change == "manifest":
        pr["manifest"]["items"] += 1
    elif change in ("slice", "inconsistent_slice"):
        for r in pr["rows"]:
            if r["item_id"] == row["item_id"]:
                r["slices"] = ["relabeled"]
                if change == "inconsistent_slice":
                    break
    elif change in ("nan", "inf"):
        pr["metrics"]["pass_rate"] = float(change)
    elif change == "missing_score":
        del row["pass_rate"]
    elif change == "null_score":
        row["pass_rate"] = None
    elif change == "row_nan":
        row["pass_rate"] = float("nan")
    elif change == "string_score":
        row["pass_rate"] = "True"
    elif change == "errors":
        pr["evaluator_failures"] = ["grader crashed on an otherwise green run"]
    blocked, lines = gate.check(pr, base, spec)
    assert blocked == ["integrity"]
    assert all("INTEGRITY" in line for line in lines)


@pytest.mark.parametrize("change", [
    "min", "max", "max_increase", "blocking", "ci", "metric", "slice",
    "slice_min", "slice_blocking", "slice_ci", "slice_metric",
])
def test_spec_ratchet(inputs, change):
    base, spec = inputs
    loose = copy.deepcopy(spec)
    metric = next(m for m in loose["metrics"] if m["id"] == "pass_rate")
    if change == "min":
        metric["threshold"]["min"] -= 0.1
    elif change == "max":
        loose["metrics"][0]["threshold"]["max"] = 1
    elif change == "max_increase":
        next(m for m in loose["metrics"] if m["id"] == "cost_per_success")["threshold"]["max_increase"] = 1
    elif change == "blocking":
        metric["blocking"] = False
    elif change == "ci":
        del metric["threshold"]["no_significant_drop"]
    elif change == "metric":
        loose["metrics"].remove(metric)
    elif change == "slice":
        loose["slices"].pop()
    elif change == "slice_min":
        del loose["slices"][0]["min"]
    elif change == "slice_blocking":
        loose["slices"][0]["blocking"] = False
    elif change == "slice_ci":
        del loose["slices"][0]["no_significant_drop"]
    elif change == "slice_metric":
        loose["slices"][0]["metric"] = "db_fact_kept"
    blocked, lines = gate.check(base, base, loose, spec)
    assert blocked == ["integrity"]
    assert any("ratchet:" in line for line in lines)


def test_honest_reports_and_stricter_spec(inputs):
    base, spec = inputs
    assert gate.check(base, base, spec, spec)[0] == []
    stricter = copy.deepcopy(spec)
    next(m for m in stricter["metrics"] if m["id"] == "pass_rate")["threshold"]["min"] = 0.90
    stricter["slices"][0]["min"] = 0.95
    assert gate.integrity_check(base, base, stricter, spec) == []
    for name in ("eval_fixed_v2.json", "eval_honest_refactor_v2.json"):
        pr = json.loads((ROOT / "reports" / name).read_text())
        pr["rows"].reverse()
        for row in pr["rows"]:
            row["slices"].reverse()
        assert gate.check(pr, base, spec, spec)[0] == []


def test_all_public_traps_fail_integrity(inputs):
    base, spec = inputs
    pr = json.loads((ROOT / "reports/eval_slice_regression.json").read_text())
    for name, (report, altered_spec) in traps.build(pr, spec).items():
        blocked, lines = gate.check(report, base, altered_spec or spec, spec)
        assert blocked == ["integrity"], (name, lines)
