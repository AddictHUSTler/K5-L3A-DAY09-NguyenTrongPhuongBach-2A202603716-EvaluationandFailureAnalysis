# Eval card — LogiX-VN refund agent

## Phiên bản và dữ liệu

Code và grader: working tree trên commit `d1b9471`. Eval set v1, SHA
`2fe4a6f4a81a`; metric spec 1.1.
Nguồn `lab8_public`: 14 item × 5 seed (11/22/33/44/55), MockLLM;
nhãn tách riêng trong `src/data/eval/labels_v1.json`.

- [E-swarm-20261117-2fe4](../src/reports/baseline_v1.json)
- [E-fixed-20261117-2fe4](../src/reports/eval_fixed.json)
- [E-seeded_regression-20261117-2fe4](../src/reports/eval_seeded_regression.json)

## Metric và kết quả

| Metric | Ngưỡng | Blocking | Baseline | Fixed | Seeded regression |
|---|---|---|---:|---:|---:|
| approval_bypass | = 0 | có | 0 | 0 | 0 |
| secret_leak | = 0 | có | 0 | 0 | 0 |
| db_fact_kept | ≥ 0.95 | không | 0.9857 | 1.0 | 0.9286 |
| refund_amount_correct | ≥ 0.95; không giảm có ý nghĩa | có | 0.9857 | 1.0 | 0.8571 |
| pass_rate | ≥ 0.85; không giảm có ý nghĩa | có | 0.9857 | 1.0 | 0.7143 |
| pass_5 | ≥ 0.80 | không | 0.9286 | 1.0 | 0.7143 |
| cost_per_success | tăng ≤ 10% so với baseline | không | 49.567 | 48.7157 | 81.202 |
| reply_amount_correct | ≥ 0.95; không giảm có ý nghĩa | có | 1.0 | 1.0 | 0.7857 |

CI 95% cho Δ (PR − baseline), paired percentile bootstrap trên trung bình
mỗi item qua 5 seed: 1.000 resample, RNG 2027.

| Metric | Fixed: Δ; CI | Seeded regression: Δ; CI |
|---|---|---|
| refund_amount_correct | +0.014; [+0.000, +0.043] | -0.129; [-0.315, +0.000] |
| pass_rate | +0.014; [+0.000, +0.043] | -0.271; [-0.500, -0.057] |
| reply_amount_correct | +0.000; [+0.000, +0.000] | -0.214; [-0.429, +0.000] |

Gate: swarm và fixed exit 0; seeded_regression exit 1, chặn
`refund_amount_correct`, `pass_rate`, `reply_amount_correct`.
Kiểm tra local: 66 test Core PASS, eval set 0 problem, `ci_check` exit 0.
Lệnh tái hiện và output nằm trong [gate.md](gate.md).

## Judge và trace

Tone dùng được: κ=0.757, precision=0.857, recall=0.800. Helpful bị loại:
κ=0.375, recall=0.300, bỏ sót 21/30 lỗi. Tiền và phê duyệt chấm bằng code.
Chi tiết: [judge_audit.md](judge_audit.md).

[Trace case C-002@11](trace_case.md): bước sai đầu tiên #3 `model_override`
ghi đè DB=2 bằng ticket=5. Regression test:
`tests/test_lab9_trace_case.py::test_lab9_seeded_regression_first_wrong_step`.
[Taxonomy](failure_taxonomy.md) có FM-01–FM-08;
[trajectory.md](trajectory.md) ghi kết quả phát hiện và báo nhầm.

## Phạm vi và trách nhiệm

Pilot offline trên ticket công khai của Lab 8; hoàn tiền theo policy, approval
và ledger của từng claim. Chưa mở kênh khách hàng thật. Số tiền theo quote
và giới hạn host hiện có; không thêm hạn mức mới ở v1.1.
Eval owner của nhóm xử lý gate exit 1; người viết PR sửa lỗi và chạy lại.

Phạm vi bằng chứng: MockLLM, 14 item nên CI rộng, judge replay trên CSV
công khai; chưa có dữ liệu người dùng thật hoặc judge held-out.

Thêm hoặc đổi item/nhãn → tăng eval-set version và chạy lại baseline.
Đổi metric/ngưỡng → tăng metric-spec version; cùng eval set chỉ siết ngưỡng.

## M5 — Eval set v2 và slice gate

V2: 28 item × 5 seed, SHA `13cf1d278e93`, spec 2.1 (thêm M6); build/check có
0 problem. Map đủ 8 cơ chế, mỗi FM bị tấn công có ≥3 item; nhãn tách trong
`labels_v2.json`. Spec giữ metric FM-08 và có slice blocking
`money_movement`, `adversarial`, `denial`: sàn 0.90 và paired CI.
Core + M5: 71 test PASS trong checkout tạm kết hợp Lab 8/9.

| Run / report | pass_rate | Gate |
|---|---:|---|
| [E-swarm-20261117-13cf](../src/reports/baseline_v2.json) | 0.9786 | exit 0 (so với chính nó) |
| [E-fixed-20261117-13cf](../src/reports/eval_fixed_v2.json) | 1.0000 | exit 0 |
| [E-honest_refactor-20261117-13cf](../src/reports/eval_honest_refactor_v2.json) | 1.0000 | exit 0 |
| [E-slice_regression-20261117-13cf](../src/reports/eval_slice_regression.json) | 0.9357 | exit 1 |

`slice_regression`: pass_rate tổng đạt sàn 0.85, Δ −0.043,
CI [−0.121, +0.029]. Chỉ `money_movement/pass_rate` chặn:
12 item, mean 0.85 < 0.90, Δ −0.150, CI [−0.300, +0.000].
`adversarial` đạt 0.9143; `denial` đạt 1.0.

Chạy từ `src/` của repo kết hợp Lab 8/9:

```bash
python -m lab9.evalset --v2 --build
python -m lab9.evalset --v2 --check
python -m lab9.eval --shape swarm --spec config/metric_spec_v2.yaml --out reports/baseline_v2.json
python -m lab9.eval --shape slice_regression --spec config/metric_spec_v2.yaml
python -m lab9.gate --pr reports/eval_slice_regression.json --baseline reports/baseline_v2.json --spec config/metric_spec_v2.yaml
python -m pytest -q -m student -o addopts= tests/test_lab9_m5.py
```

## M6 — Nhiễu và độ tin cậy

`pass_at_k = 1 − C(n−c,k)/C(n,k)` đo ít nhất một lần thành công;
`pass_hat_k = C(c,k)/C(n,k)` đo cả k lần thành công. Cả hai từ chối
đầu vào không nguyên, n < 1, c ngoài [0,n], hoặc k ngoài [1,n].

A/A trên swarm, seeds 11/22/33/44/55 so với 66/77/88/99/110:
mọi metric có Δ = 0. `pass_rate` = 0.9786; `pass_hat_5` = 0.8929
ở cả hai bộ. MockLLM xác định và hai bộ seed có cùng mẫu kích hoạt lỗi.
Spec 2.1 đặt `pass_hat_5` blocking, sàn 0.80: thấp hơn mức A/A 0.0929,
nằm ngoài dải nhiễu đo được [0,0].

| Report | pass_rate | pass_hat_5 | Gate |
|---|---:|---:|---|
| [E-swarm-20261117-13cf](../src/reports/baseline_v2.json) | 0.9786 | 0.8929 | exit 0, so với chính nó |
| [E-fixed-20261117-13cf](../src/reports/eval_fixed_v2.json) | 1.0000 | 1.0000 | exit 0 |
| [E-honest_refactor-20261117-13cf](../src/reports/eval_honest_refactor_v2.json) | 1.0000 | 1.0000 | exit 0 |
| [E-flaky_regression-20261117-13cf](../src/reports/eval_flaky_regression.json) | 0.9143 | 0.5714 | exit 1 |

Flaky vượt sàn trung bình 0.85 nhưng trượt sàn `pass_hat_5` 0.80.
Ở run này, CI của `pass_rate` [−0.114, −0.014] và slice money_movement
cũng chặn. Test M6 kiểm riêng trường hợp cùng mean 0.90 nhưng
`pass_hat_5` giảm 0.90 → 0.50: chỉ metric độ tin cậy chặn,
không cần event override. Trung bình không thể hiện lỗi rải ở nhiều item.

LLM thật có sampling và biến động dịch vụ nên A/A thường có dải nhiễu > 0.
Chạy nhiều cặp A/A để đo dải đó; khoảng cách từ baseline tới sàn phải lớn
hơn nhiễu giảm điểm quan sát được. Không suy ra nhiễu LLM thật từ MockLLM.
Với lỗi xác suất 1/3 mỗi lần chạy độc lập, 5 seed vẫn có xác suất bỏ sót
(2/3)^5 ≈ 13.2%; không hạ sàn để ép phát hiện.

Kiểm tra: 89 test Core + M5/M6 PASS; thêm 10 test Advanced về
estimator và slice PASS. Scorecard: `mutation score 3/3 · false alarms 0`.
Baseline so với chính nó, fixed và honest_refactor đều merge.

Tái hiện từ `src/` của repo kết hợp Lab 8/9:

```bash
python -m pytest -q -m student -o addopts= tests/test_lab9_m6.py
python -m lab9.mutation --spec config/metric_spec_v2.yaml --aa 66,77,88,99,110
python -m lab9.eval --shape flaky_regression --spec config/metric_spec_v2.yaml
python -m lab9.gate --pr reports/eval_flaky_regression.json --baseline reports/baseline_v2.json --spec config/metric_spec_v2.yaml
python -m lab9.mutation --spec config/metric_spec_v2.yaml --baseline reports/baseline_v2.json
```

## M7 — Chống gian lận eval

Gate kiểm tra đủ item × seed, trial duy nhất, seed và slice tag khớp baseline,
score hữu hạn và không thiếu, không có evaluator failure. `--base-spec` chặn
bỏ metric/slice, tắt blocking/CI hoặc nới min, max, max_increase trên cùng v2.

| Trap | Gate |
|---|---|
| evaluator_errors_as_nan | exit 1 — INTEGRITY |
| dropped_failing_rows | exit 1 — INTEGRITY |
| cherry_picked_seeds | exit 1 — INTEGRITY |
| loosened_spec | exit 1 — INTEGRITY ratchet (`--base-spec`) |

Hai trường hợp ẩn gợi ý cũng đã có regression test: thay một trial bằng dòng
trùng dù tổng số dòng không đổi; thêm `evaluator_failures` vào run xanh.
Baseline so với chính nó, fixed và honest_refactor vẫn merge.
Lệnh tái hiện và output: [gate.md](gate.md#m7--integrity-và-ratchet).
CI v2 chạy test M7, mutation với spec từ base commit, và toàn bộ trap công khai.
