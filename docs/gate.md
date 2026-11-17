# Gate — M4

Eval set `2fe4a6f4a81a`, metric spec v1.1, 14 items × seeds 11/22/33/44/55.
Baseline: `E-swarm-20261117-2fe4` (`src/reports/baseline_v1.json`).

`paired_bootstrap` compares per-item seed means, PR minus baseline, using SciPy's
paired percentile bootstrap: 1,000 resamples, RNG 2027, confidence 95%.
Identical inputs return `(0, 0, 0)`.

| Run | pass_rate | Δ vs baseline | 95% CI | Gate exit |
|---|---:|---:|---|---:|
| E-swarm-20261117-2fe4 (fresh PR run) | 0.9857 | 0.000 | [0.000, 0.000] | 0 |
| E-fixed-20261117-2fe4 | 1.0000 | +0.014 | [0.000, +0.043] | 0 |
| E-seeded_regression-20261117-2fe4 | 0.7143 | −0.271 | [−0.500, −0.057] | 1 |

Regression output for the PR description:

```text
pass_rate  0.7143  Δ -0.271 CI [-0.500, -0.057] BLOCK
exit 1 — blocked: refund_amount_correct, pass_rate, reply_amount_correct
```

Local checks: 66 core student tests passed; eval set has 0 problems; smoke,
fresh swarm gate and `lab9.ci_check` all exited 0. The regression CI matches
the checkpoint reference to three decimal places.

Reproduce from the combined Lab 8/9 `src/`:

```bash
python -m pytest -q -m student -o addopts= -k "lab9 and not advanced"
python -m lab9.evalset --check
python -m lab9.eval --shape swarm --out reports/baseline_v1.json
python -m lab9.eval --shape fixed
python -m lab9.gate --pr reports/eval_fixed.json --baseline reports/baseline_v1.json
python -m lab9.eval --shape seeded_regression
python -m lab9.gate --pr reports/eval_seeded_regression.json --baseline reports/baseline_v1.json
```

`src/harness_map.yaml` v1.2 includes `sections.eval`. The three generated
M4 reports are included by `.gitignore`; other reports remain ignored.
