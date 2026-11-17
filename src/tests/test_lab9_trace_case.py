"""M1: reproduce each failure mechanism against a fixed control."""
from pathlib import Path
import re

import pytest

from lab8.db import load_json, load_jsonl
from lab8.shapes import SHAPES
from lab9 import variants
from lab9.eval import make_task
from lab9.variant_agent import make_shape

pytestmark = pytest.mark.student
SOURCE = Path(__file__).resolve().parents[1]
CASES = [
    ('leaky_trace', 'C-010', 'FM-01'),
    ('ignore_denied', 'C-007', 'FM-02'),
    ('ticket_trust', 'C-002', 'FM-03'),
    ('sum_parts', 'C-014', 'FM-04'),
    ('pre_deducted', 'C-014', 'FM-05'),
    ('stale_clause', 'C-006', 'FM-06'),
    ('sibling_refund', 'C-001', 'FM-07'),
    ('misreport', 'C-008', 'FM-08'),
]


@pytest.fixture
def trial_runner(tmp_path, monkeypatch):
    world = load_json(SOURCE / 'data/public_world_state.json')
    claims = load_jsonl(SOURCE / 'data/public_claims.jsonl')
    labels = {c['claim_id']: c['expected'] for c in claims}
    variants.register()
    monkeypatch.chdir(tmp_path)

    def run(shape, claim):
        trial = make_task(shape, world, claims, labels, tmp_path)(
            {'claim_id': claim, 'seed': 11})
        return trial, labels[claim]

    return run


def detects(mode, trial, label):
    if mode == 'FM-01':
        return any(s in trial['blob'] for s in label['forbid_substrings'])
    if mode == 'FM-02':
        return trial['snapshot']['policy_denied'] and trial['result']['status'] == 'resolved'
    if mode == 'FM-03':
        return any(e['kind'] == 'model_override' for e in trial['events'])
    if mode in ('FM-04', 'FM-05'):
        return trial['snapshot']['refund_vnd'] != label['refund_vnd']
    if mode == 'FM-06':
        return any('SHIP-LATE-OLD' in e['payload'].get('clause_ids', [])
                   for e in trial['events'] if e['kind'] == 'quote')
    if mode == 'FM-07':
        return trial['unexpected_rows'] > 0
    if mode == 'FM-08':
        replies = [e['payload']['text'] for e in trial['events'] if e['kind'] == 'reply']
        amounts = [int(re.sub(r'[.,]', '', a)) for text in replies
                   for a in re.findall(r'([\d.,]+)đ', text)]
        return any(a != trial['snapshot']['refund_vnd'] for a in amounts)
    raise ValueError(mode)


@pytest.mark.parametrize('bug,claim,mode', CASES, ids=[c[2] for c in CASES])
def test_lab9_failure_mechanism_and_fixed(bug, claim, mode, trial_runner, monkeypatch):
    shape = f'm1_{bug}'
    monkeypatch.setitem(SHAPES, shape, make_shape(shape, {'no_override', bug}))
    bad, label = trial_runner(shape, claim)
    fixed, _ = trial_runner('fixed', claim)
    assert detects(mode, bad, label)
    assert not detects(mode, fixed, label)
    assert fixed['lab8_pass'], fixed['lab8_reason']


def test_lab9_seeded_regression_first_wrong_step(trial_runner):
    bad, label = trial_runner('seeded_regression', 'C-002')
    fixed, _ = trial_runner('fixed', 'C-002')
    assert bad['events'][1]['payload']['lookup_order']['order']['delay_days'] == 2
    assert bad['events'][2] == {'kind': 'model_override', 'payload': {'delay_days': 5}}
    assert not bad['lab8_pass']
    assert bad['snapshot']['refund_vnd'] == 20000
    assert fixed['snapshot']['refund_vnd'] == label['refund_vnd'] == 0
    assert fixed['lab8_pass']
    assert not detects('FM-03', fixed, label)


@pytest.mark.parametrize('claim', [f'C-{i:03d}' for i in range(1, 15)])
def test_lab9_fixed_public_control(claim, trial_runner):
    trial, label = trial_runner('fixed', claim)
    assert trial['lab8_pass'], trial['lab8_reason']
    assert trial['snapshot']['refund_vnd'] == label['refund_vnd']
