# Trace case: C-002@11

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11`; run ID `R-seeded_regression-C-002-s11` |
| Triệu chứng | Ledger ghi 20.000đ / 1 refund; nhãn yêu cầu 0đ / 0 refund, status `denied`. Lab 8: `status resolved != denied`. |
| Bước sai đầu tiên | #3 `model_override {"delay_days":5}` |
| Vì sao đầu tiên | #1 handoff chỉ cho phép các tool đọc; #2 investigator trả đúng O-202 với `delay_days=2`; #3 mới ghi đè bằng ticket. |
| Hậu quả | #4 quote 20.000đ, #5 history rỗng, #6 reply báo đã hoàn 20.000đ; ledger xác nhận khoản sai. |
| Failure mode | FM-03 `ticket_trust` |
| Đối chứng | `R-fixed-C-002-s11`: giữ DB=2; #3 quote 0 (`no_entitlement`), #4 reply từ chối; ledger 0, Lab 8 PASS. |
| Regression test | `tests/test_lab9_trace_case.py::test_lab9_seeded_regression_first_wrong_step`: xác nhận DB=2 rồi override=5; bad FAIL với ledger 20.000đ, fixed PASS với ledger 0. |
| Chưa chắc chắn | Trace cho thấy dữ kiện bị thay; không chứng minh suy nghĩ nội bộ của model. |

Tái hiện từ `src/`:

```bash
python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
python -m lab9.trace_case --shape fixed --claim C-002 --seed 11
python -m pytest -q -m student -o addopts= tests/test_lab9_trace_case.py
```

Các bằng chứng FM khác và bước sai đầu tiên nằm trong [taxonomy](failure_taxonomy.md).
