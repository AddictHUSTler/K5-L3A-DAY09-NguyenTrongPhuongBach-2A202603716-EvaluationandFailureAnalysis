"""M6: reliability probabilities, argument validation and intermittent failures."""
from itertools import combinations
from pathlib import Path

import pytest

from lab9 import gate, stats
from lab9.eval import aggregate, load_spec

pytestmark = pytest.mark.student


def test_estimators_match_all_draws():
    for n in range(1, 9):
        for c in range(n + 1):
            trials = [True] * c + [False] * (n - c)
            for k in range(1, n + 1):
                draws = list(combinations(trials, k))
                at = stats.pass_at_k(n, c, k)
                hat = stats.pass_hat_k(n, c, k)
                assert at == pytest.approx(sum(any(d) for d in draws) / len(draws))
                assert hat == pytest.approx(sum(all(d) for d in draws) / len(draws))
                assert hat <= c / n + 1e-12
                assert at >= c / n - 1e-12


@pytest.mark.parametrize("args", [
    (0, 0, 1), (-1, 0, 1), (5, -1, 1), (5, 6, 1),
    (5, 2, 0), (5, 2, -1), (3, 1, 4),
    (5.0, 2, 1), (5, 2.0, 1), (5, 2, 1.0),
    (True, 1, 1), (5, False, 1), (5, 2, True),
    ("5", 2, 1), (None, 2, 1), (5, float("nan"), 1),
])
def test_both_estimators_reject_invalid_inputs(args):
    for estimator in (stats.pass_at_k, stats.pass_hat_k):
        with pytest.raises(ValueError):
            estimator(*args)


def test_reliability_gate_catches_one_in_five_without_override_event():
    spec = load_spec(Path(__file__).resolve().parents[1] / "config/metric_spec_v2.yaml")
    metric = next(m for m in spec["metrics"] if m["id"] == "pass_hat_5")
    assert metric["blocking"] and metric["threshold"]["min"] >= 0.8
    # The same per-item mean (0.9) hides very different reliability.
    def report(intermittent):
        rows = [
            {"item_id": str(i), "seed": s, "cost": 1,
             "pass_rate": not (i < 5 and s == 0) if intermittent else i != 0}
            for i in range(10) for s in range(5)
        ]
        return {"manifest": {"eval_set_sha": "test", "items": 10, "seeds": list(range(5))},
                "rows": rows, "evaluator_failures": [],
                "metrics": aggregate(rows, ["pass_rate"], [1, 3, 5])}

    base, pr = report(False), report(True)
    assert base["metrics"]["pass_rate"] == pr["metrics"]["pass_rate"] == 0.9
    assert base["metrics"]["pass_hat_5"] == 0.9
    assert pr["metrics"]["pass_hat_5"] == 0.5
    gate_spec = {"metrics": [metric, {"id": "pass_rate", "blocking": True,
                                    "threshold": {"min": 0.85}}]}
    assert gate.check(base, base, gate_spec)[0] == []
    assert gate.check(pr, base, gate_spec)[0] == ["pass_hat_5"]
