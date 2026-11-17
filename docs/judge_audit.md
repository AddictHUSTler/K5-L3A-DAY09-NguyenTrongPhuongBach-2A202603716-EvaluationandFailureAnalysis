# Judge audit — M2

FAIL là lớp dương. Ngưỡng: κ ≥ 0.6, precision ≥ 0.8, recall ≥ 0.7.

| Tiêu chí | n | TP / FP / FN / TN | κ | Precision | Recall | Quyết định |
|---|---:|---|---:|---:|---:|---|
| tone_ok | 100 | 24 / 4 / 6 / 66 | 0.757 | 0.857 | 0.800 | PASS: dùng cho tone |
| helpful | 100 | 9 / 0 / 21 / 70 | 0.375 | 1.000 | 0.300 | FAIL: không dùng làm gate |

Tỉ lệ FAIL quan sát → Rogan–Gladen: tone 0.280 → 0.300; helpful 0.090 → 0.300.

| Case | Judge | Người | Ai đúng, vì sao | Sửa rubric / nhãn |
|---|---|---|---|---|
| H-008 | PASS | FAIL | Người: “em”, “nha”, “anh check” quá suồng sã. | FAIL với cách xưng hô suồng sã trong khiếu nại. |
| H-017 | PASS | FAIL | Người: gọi khách lớn tuổi là “bạn”, dùng “nha”. | Chấm xưng hô theo ngữ cảnh khách, không đồng nhất thân thiện với phù hợp. |
| H-029 | PASS | FAIL | Người: “không cần nhắn thêm” mang giọng ra lệnh. | Chấm toàn câu; “Dạ, vui lòng” không bù được lời ra lệnh. |
| H-042 | FAIL | PASS | Người: câu ngắn vẫn lịch sự, đủ kết quả và thời gian nhận tiền. | Không bắt buộc xin lỗi trong mọi reply. |
| H-051 | FAIL | PASS | Người: CS cho phép từ “refund”. | Cho phép thuật ngữ đã được duyệt. |
| H-081 | FAIL | PASS | Judge đúng theo note: người đọc nhầm ticket. | Đề nghị sửa nhãn thành FAIL sau đối chiếu ticket; giữ CSV gốc để tái hiện calibration. |
| HL-015 | PASS | FAIL | Người: reply 55.000đ, ledger 40.000đ. | Sai tiền là FAIL dù lịch sự; đối chiếu bằng code. |
| HL-016 | PASS | FAIL | Người: reply 55.000đ, ledger 35.000đ; lời xin lỗi che lỗi tiền. | Chấm đúng kết quả trước lời văn; lời xin lỗi không bù sai tiền. |
| HL-047 | PASS | FAIL | Người: “Ok bạn… nhé” sai xưng hô. | Tách tone khỏi tính đúng và đủ của câu trả lời. |

Helpful bỏ sót 21/30 lỗi (70%). Precision cao không bù được recall 0.300 và κ 0.375: dùng làm gate sẽ cho qua nhiều reply sai. Tiền và phê duyệt dùng code; chỉ tone đã đạt calibration mới dùng judge.

Tái hiện từ `src/`:

```bash
python -m pytest -q -m student -o addopts= tests/test_lab9_stats.py tests/test_lab9_calibration.py -k 'not paired_bootstrap'
python -m lab9.judge --csv data/eval/judge_tone_public.csv --audit 5
python -m lab9.judge --csv data/eval/judge_helpful_public.csv --audit 5
```

Tone exit 0; helpful exit 1.
