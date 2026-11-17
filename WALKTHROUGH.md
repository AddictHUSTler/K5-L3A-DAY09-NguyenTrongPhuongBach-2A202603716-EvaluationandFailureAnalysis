# Lab 9: the short walkthrough

**Goal:** build an evaluation system that accepts a good agent change and blocks a bad one before merge.

Day 8 built refund agents. Day 9 reuses their code, claims, ledger and traces to measure correctness. You use the supplied `swarm` reference; unfinished Day 8 `workflow` / `single` / `orchestrator` implementations do not block this lab. No API key needed.

## 0. Put Day 9 inside Day 8

This checkout is an **overlay**, not a standalone project. The intended submission lives in your Day 8 team repo.

For your local paths:

```bash
cd /home/f/K5-L3A-DAY08-LLC-From-Workflows-to-Agents
git switch -c starter/d09
cp -R /home/f/K5-L3A-DAY09-LLC-EvaluationAndFailureAnalysis/src/. src/
cp -R /home/f/K5-L3A-DAY09-LLC-EvaluationAndFailureAnalysis/docs/. docs/
cp -R /home/f/K5-L3A-DAY09-LLC-EvaluationAndFailureAnalysis/.github/. .github/

cd src
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt -r requirements-lab9.txt
python -m lab9.smoke
python -m lab9.evalset --build
```

Expected: `M0 PASS`, then 14 eval items plus a separate labels file. Empty `failure_modes` are allowed at this initial build.

Keep Day 8's root README, `.gitignore` and other root files. Check `git status`: the overlay should add files without changing `src/lab8/`.

**All Python commands below run from the combined repo's `src/`.** Documentation paths such as `docs/...` are relative to its root.

## 1. Name the failures — M1

Complete `docs/failure_taxonomy.md`: at least five failure modes, each with a definition, layer, actual trace evidence (`claim@seed`), grader and metric. Keep the supplied FM codes and short names.

Inspect a faulty run beside a good run:

```bash
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11
```

Read the ledger, then find the **first wrong trace event**. Repeat with other claims as needed; the rubric includes five mandatory anchor cases. Complete `docs/trace_case.md` for one failing case and add a runnable regression test showing failure on the bad variant and success on `fixed`.

Implement the claim-to-FM mapping in `lab9/evalset.py`, rebuild, then check:

```bash
python -m lab9.evalset --build
python -m lab9.evalset --check
```

Expected: `0 problem(s)`. Keep answers in `labels_v1.json`, separate from input items. Put the mapping in the builder so rebuilding preserves it.

## 2. Check whether the judge is trustworthy — M2

Implement `confusion`, `precision_recall`, `cohen_kappa` and `rogan_gladen` in `lab9/stats.py`. **FAIL is the positive class**: you are measuring whether the judge finds failures. Undefined kappa must fail calibration.

```bash
python -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 5
python -m lab9.judge --csv data/eval/judge_helpful_public.csv --audit 5
```

Expected: tone passes (`κ≈0.757`, precision `≈0.857`, recall `0.8`); helpful fails. That second exit 1 is intentional.

In `docs/judge_audit.md`, record both results and review at least five disagreements: who was right, why, and how to improve the rubric. Only calibrated criteria may use a judge. Money and approvals use code.

## 3. Implement the graders — M3

In `lab9/graders.py`:

| Grader | Required behavior |
|---|---|
| `ApprovalBypass` | Return true for a refund without valid approval, or an unauthorized ledger row. True means a safety failure. |
| `RefundAmountCorrect` | Compare the ledger refund amount with the expected amount. True means correct. |
| Your FM-08 grader | Catch a reply that claims a different refund amount from the ledger. |

Register your FM-08 grader in `GRADERS` and add its metric to `config/metric_spec.yaml` as a **blocking capability metric**. A YAML entry alone does not implement the grader.

Target: detect at least 80% of faulty traces, with at most 10% false alarms on `fixed`.

## 4. Compare versions and block regressions — M4

Implement `paired_bootstrap` in `lab9/stats.py`: compare PR minus baseline using **per-item means across seeds**, paired on the same items. Use the specified SciPy percentile bootstrap. Identical inputs return `(0, 0, 0)`.

The core comparison logic is already in `gate.py`. A blocking metric fails if it misses its threshold or its configured paired CI is entirely below zero.

```bash
python -m pytest -q -m student -o addopts= -k "lab9 and not advanced"

python -m lab9.eval --shape swarm --out reports/baseline_v1.json
python -m lab9.eval --shape fixed
python -m lab9.gate --pr reports/eval_fixed.json --baseline reports/baseline_v1.json

python -m lab9.eval --shape seeded_regression
python -m lab9.gate --pr reports/eval_seeded_regression.json --baseline reports/baseline_v1.json
```

Expected: tests pass; `fixed` gate exits 0; `seeded_regression` gate exits 1 and explicitly blocks `pass_rate`. A Python crash does not count as a successful block.

## 5. Finish the core submission — 60 points

- Fill `docs/eval_card.md` and `docs/PRD_v1.1.md` using generated results and run IDs. State the limits: MockLLM, 14 items × 5 seeds, replayed judge labels.
- Merge `src/harness_map.eval.yaml` into `src/harness_map.yaml` under `sections:`; bump `harness_map_version` to `"1.2"`.
- Commit the generated baseline and both variant reports. Reports are ignored by Git; use `git add -f` for these files.
- Open the submission PR from `starter/d09` to the team repo's `main`. Include the regression gate output. The supplied CI runs on PRs or manual dispatch; `eval-gate` must be green.

Never edit `lab8/`, hand-edit reports, or loosen thresholds to force a pass.

## 6. Remaining 40 points — M5–M7

| Stage | Implement | Prove |
|---|---|---|
| M5: small groups of cases | Fill `fm_map.yaml`; build v2; add blocking `money_movement` and `adversarial` slices; implement `gate.slice_check`; carry over FM-08. | Each attacked FM has ≥3 items in v2. Block `slice_regression`. |
| M6: reliability | Implement `pass_at_k` (at least one success) and `pass_hat_k` (all succeed); validate inputs; add blocking `pass_hat_5`. | Measure A/A noise with alternate seeds. Choose a floor outside that noise, at least 0.8. Block `flaky_regression`. |
| M7: trustworthy reports | Implement `gate.integrity_check` and threshold ratcheting with `--base-spec`. | Reject missing/duplicate trials, cherry-picked seeds, invalid values, evaluator errors, changed slice tags and weakened specs. |

After implementing those pieces:

```bash
python -m lab9.evalset --v2 --build
python -m lab9.eval --shape swarm --spec config/metric_spec_v2.yaml --out reports/baseline_v2.json
python -m lab9.mutation --spec config/metric_spec_v2.yaml --aa 66,77,88,99,110
python -m lab9.mutation --spec config/metric_spec_v2.yaml --baseline reports/baseline_v2.json
python -m lab9.eval --shape slice_regression --spec config/metric_spec_v2.yaml --out reports/eval_slice_regression.json
python -m lab9.traps --pr reports/eval_slice_regression.json --baseline reports/baseline_v2.json --spec config/metric_spec_v2.yaml
python -m pytest -q -m student -o addopts= -k advanced
```

Expected: mutation scorecard blocks 3/3 regressions and accepts `fixed` / `honest_refactor`; every trap is blocked. The overall mutation and traps commands exit 0 when their checks succeed. Exercise ratcheting separately with `--base-spec` pointing to the protected baseline's spec.

Commit the v2 data and baseline, extend the eval card with noise/slice results and sample-size limits, and include mutation/A/A/trap output in the PR. Committing `baseline_v2.json` enables the advanced CI checks. Hidden tests check behavior, so do not hardcode variant names.

Source of requirements: [README](README.md), [checkpoints](CHECKPOINTS.md), [rubric](RUBRIC.md), [submission checklist](SUBMISSION.md).
