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

## M7 — Integrity và ratchet

V2 dùng baseline `E-swarm-20261117-13cf`, SHA `13cf1d278e93`, spec 2.1.
Chạy từ `src/` của repo kết hợp Lab 8/9:

```bash
python -m pytest -q -m student -o addopts= -k "advanced or m7"
python -m lab9.mutation --spec config/metric_spec_v2.yaml --baseline reports/baseline_v2.json --base-spec config/metric_spec_v2.yaml
python -m lab9.traps --pr reports/eval_slice_regression.json --baseline reports/baseline_v2.json --spec config/metric_spec_v2.yaml
```

`traps` sinh file trong `reports/traps/` và in lệnh gate riêng cho từng file.
Đã chạy riêng cả bốn lệnh, đều exit 1 với lý do `INTEGRITY`:

```text
evaluator_errors_as_nan.json: exit 1 — INTEGRITY PR: invalid grader value refund_amount_correct at E-014@11
dropped_failing_rows.json: exit 1 — INTEGRITY PR: row count differs from manifest items × seeds
cherry_picked_seeds.json: exit 1 — INTEGRITY PR: invalid metric pass_hat_3
loosened_spec.json: exit 1 — INTEGRITY ratchet: metrics:db_fact_kept loosened min
```

Lệnh `loosened_spec` dùng `--spec reports/traps/loosened_spec.spec.yaml`
và `--base-spec config/metric_spec_v2.yaml`. Trong CI, `--base-spec` của mutation
lấy từ base commit của PR; workflow dispatch dùng commit hiện tại.

Kiểm tra local trong checkout tạm kết hợp Lab 8/9: 128 student test PASS
(3 deselected), gồm 27 test M7. Mutation exit 0:

```text
fixed                expect merge got merge ok
honest_refactor      expect merge got merge ok
seeded_regression    expect block got block ok
slice_regression     expect block got block ok
flaky_regression     expect block got block ok
mutation score 3/3 · false alarms 0
```

A/A chạy lại với seeds 66/77/88/99/110: mọi metric có Δ = 0, exit 0.
