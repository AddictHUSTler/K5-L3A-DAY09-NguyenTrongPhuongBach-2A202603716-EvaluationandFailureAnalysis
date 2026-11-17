"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item
from lab9.graders import GRADERS


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    problems = []

    def finite(value):
        return isinstance(value, (int, float)) and math.isfinite(value)

    graded = {m["id"] for m in spec["metrics"]
              if m["id"] in GRADERS or m.get("grader") == "code"
              or any(m["id"] in row for row in base.get("rows", []))}
    if any(m["id"].startswith(("pass_at_", "pass_hat_", "pass_"))
           or m["id"] == "cost_per_success" for m in spec["metrics"]):
        graded.add("pass_rate")
    pairs, tags = {}, {}
    for name, report in (("PR", pr), ("baseline", base)):
        manifest = report.get("manifest", {})
        rows = report.get("rows", [])
        seeds = manifest.get("seeds", [])
        items = manifest.get("items")
        if (not seeds or any(type(s) is not int for s in seeds)
                or len(set(seeds)) != len(seeds)
                or type(items) is not int or items < 1):
            problems.append(f"{name}: invalid item/seed manifest")
            continue
        if len(rows) != items * len(seeds):
            problems.append(f"{name}: row count differs from manifest items × seeds")
        if report.get("evaluator_failures"):
            problems.append(f"{name}: evaluator_failures is non-empty")
        metrics = report.get("metrics", {})
        for mid in set(metrics) | {m["id"] for m in spec["metrics"]}:
            if not finite(metrics.get(mid)):
                problems.append(f"{name}: invalid metric {mid}")
        counts, item_tags = Counter(), {}
        for row in rows:
            item, seed = row.get("item_id"), row.get("seed")
            if not isinstance(item, str) or type(seed) is not int:
                problems.append(f"{name}: invalid trial identity")
                continue
            counts[item, seed] += 1
            if "cost" in row and (not finite(row["cost"]) or row["cost"] < 0):
                problems.append(f"{name}: invalid cost at {item}@{seed}")
            slices = row.get("slices", [])
            if not isinstance(slices, list) or any(not isinstance(s, str) for s in slices):
                problems.append(f"{name}: invalid slice tags for {item}")
                continue
            tag_set = frozenset(slices)
            if item in item_tags and item_tags[item] != tag_set:
                problems.append(f"{name}: inconsistent slice tags for {item}")
            item_tags[item] = tag_set
            for mid in graded:
                if not finite(row.get(mid)) or row[mid] not in (0, 1):
                    problems.append(f"{name}: invalid grader value {mid} at {item}@{seed}")
        if any(n != 1 for n in counts.values()):
            problems.append(f"{name}: duplicate trials")
        item_ids = {item for item, _ in counts}
        if len(item_ids) != items or set(counts) != {(i, s) for i in item_ids for s in seeds}:
            problems.append(f"{name}: incomplete item × seed coverage")
        pairs[name], tags[name] = set(counts), item_tags
        if "seeds" in spec and set(seeds) != set(spec["seeds"]):
            problems.append(f"{name}: seeds differ from spec")
    if pairs.get("PR") != pairs.get("baseline"):
        problems.append("PR trials differ from baseline (item_id, seed) pairs")
    if tags.get("PR") != tags.get("baseline"):
        problems.append("PR item slice tags differ from baseline")

    if base_spec is not None and spec.get("eval_set_version") == base_spec.get("eval_set_version"):
        def ratchet(old, new, label):
            if old.get("blocking") and not new.get("blocking"):
                problems.append(f"ratchet: {label} is no longer blocking")
            for key in ("min", "max", "max_increase"):
                if key in old and (key not in new or not finite(new[key])
                                   or (new[key] < old[key] if key == "min" else new[key] > old[key])):
                    problems.append(f"ratchet: {label} loosened {key}")
            if old.get("no_significant_drop") and not new.get("no_significant_drop"):
                problems.append(f"ratchet: {label} dropped no_significant_drop")

        for group, identity in (("metrics", lambda m: m["id"]),
                                ("slices", lambda s: (s["name"], s["metric"]))):
            entries = {identity(e): e for e in spec.get(group, [])}
            for old in base_spec.get(group, []):
                key = identity(old)
                label = f"{group}:{key}"
                if key not in entries:
                    problems.append(f"ratchet: removed {label}")
                    continue
                new = entries[key]
                ratchet(old, new, label)
                if group == "metrics":
                    ratchet(old.get("threshold", {}), new.get("threshold", {}), label)
    return problems


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for entry in spec.get("slices", []):
        name, metric = entry["name"], entry["metric"]
        sid = f"slice:{name}/{metric}"
        a, b = per_item(pr, metric, slice_name=name), per_item(base, metric, slice_name=name)
        value = sum(a.values()) / len(a) if a else None
        failed = value is None or ("min" in entry and value < entry["min"])
        note = ""
        if entry.get("no_significant_drop"):
            if not a or a.keys() != b.keys():
                failed, note = True, "missing paired items"
            elif len(a) < 2:
                failed, note = True, "paired CI needs at least two items"
            else:
                keys = sorted(a)
                delta, lo, hi = stats.paired_bootstrap(
                    [a[k] for k in keys], [b[k] for k in keys],
                    n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                    confidence=bs.get("confidence", 0.95),
                )
                note = f"Δ {delta:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
                failed = failed or hi < 0
        if failed and entry.get("blocking"):
            blocked.append(sid)
        verdict = ("BLOCK" if entry.get("blocking") else "warn") if failed else "ok"
        lines.append(f"  {sid:<40} {value!s:<8} {note:<30} {verdict}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
