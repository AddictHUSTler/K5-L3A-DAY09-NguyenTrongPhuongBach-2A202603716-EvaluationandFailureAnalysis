"""M2: calibration boundaries and public judge decisions."""
from pathlib import Path

import pytest

from lab9 import stats
from lab9.judge import calibrate

pytestmark = pytest.mark.student


def test_lab9_public_judge_decisions():
    assert calibrate(Path('data/eval/judge_tone_public.csv'))['passed']
    helpful = calibrate(Path('data/eval/judge_helpful_public.csv'))
    assert not helpful['passed']
    assert helpful['confusion'] == dict(tp=9, fp=0, fn=21, tn=70)


def test_lab9_precision_recall_no_positive_predictions():
    assert stats.precision_recall(['PASS', 'FAIL'], ['PASS', 'PASS']) == (0, 0)
    assert stats.precision_recall(['PASS'], ['FAIL']) == (0, 0)


@pytest.mark.parametrize('human,judge', [([], []), (['PASS'], []), (['bad'], ['PASS'])])
def test_lab9_confusion_rejects_invalid_labels(human, judge):
    with pytest.raises(ValueError):
        stats.confusion(human, judge)


def test_lab9_rogan_gladen_upper_clip_and_undefined():
    assert stats.rogan_gladen(1, 0.8, 0.9) == 1
    with pytest.raises(ValueError):
        stats.rogan_gladen(0.2, 0.5, 0.5)


def test_lab9_constant_judge_fails_cleanly(tmp_path):
    path = tmp_path / 'constant.csv'
    path.write_text('item_id,reply,human,judge\nx,ok,PASS,PASS\n')
    result = calibrate(path)
    assert not result['passed']
    assert result['corrected_fail_rate'] is None
