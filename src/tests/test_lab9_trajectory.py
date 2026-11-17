"""M3: real trajectories, currency formats, and honest controls."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from lab8.db import load_json, load_jsonl
from lab8.shapes import SHAPES
from lab9 import variants
from lab9.eval import make_task, load_spec, run_eval
from lab9.evalset import load_jsonl as load_items
from lab9.graders import GRADERS, ReplyAmountCorrect
from lab9.variant_agent import make_shape

pytestmark = pytest.mark.student
SOURCE = Path(__file__).resolve().parents[1]
SEEDS = [11, 22, 33, 44, 55]
ANCHORS = [
    ('leaky_trace', 'C-010', 'secret_leak'),
    ('ignore_denied', 'C-007', 'pass_rate'),
    ('ticket_trust', 'C-002', 'db_fact_kept'),
    ('sum_parts', 'C-014', 'refund_amount_correct'),
    ('pre_deducted', 'C-014', 'refund_amount_correct'),
    ('stale_clause', 'C-006', 'pass_rate'),
    ('sibling_refund', 'C-001', 'approval_bypass'),
    ('misreport', 'C-008', 'reply_amount_correct'),
]


def failed(metric, trial, label):
    value = GRADERS[metric]().evaluate(SimpleNamespace(output=trial, expected_output=label)).value
    return value if metric in ('secret_leak', 'approval_bypass') else not value


@pytest.fixture
def runner(tmp_path, monkeypatch):
    world = load_json(SOURCE / 'data/public_world_state.json')
    claims = load_jsonl(SOURCE / 'data/public_claims.jsonl')
    labels = {c['claim_id']: c['expected'] for c in claims}
    variants.register()
    monkeypatch.chdir(tmp_path)

    def run(shape, claim, seed):
        return make_task(shape, world, claims, labels, tmp_path)({'claim_id': claim, 'seed': seed}), labels[claim]

    return run


@pytest.mark.parametrize('bug,claim,metric', ANCHORS)
def test_lab9_fault_detection_across_seeds(bug, claim, metric, runner, monkeypatch):
    shape = f'm3_{bug}'
    monkeypatch.setitem(SHAPES, shape, make_shape(shape, {'no_override', bug}))
    detected = sum(failed(metric, *runner(shape, claim, seed)) for seed in SEEDS)
    assert detected == len(SEEDS)


@pytest.mark.parametrize('shape', ['fixed', 'honest_refactor'])
def test_lab9_controls_have_no_false_alarms(shape, runner):
    alarms = 0
    for claim in [f'C-{i:03}' for i in range(1, 15)]:
        for seed in SEEDS:
            trial, label = runner(shape, claim, seed)
            alarms += any(failed(metric, trial, label) for metric in GRADERS)
    assert alarms == 0  # 0/70 for each control


@pytest.mark.parametrize('shape', ['seeded_regression', 'slice_regression', 'flaky_regression'])
def test_lab9_public_variant_detection(shape, runner):
    faulty = detected = 0
    for claim in [f'C-{i:03}' for i in range(1, 15)]:
        for seed in SEEDS:
            trial, label = runner(shape, claim, seed)
            if not trial['lab8_pass']:
                faulty += 1
                detected += any(failed(metric, trial, label) for metric in GRADERS)
    print(f'{shape}: grader suite detected {detected}/{faulty} faulty traces')
    assert faulty > 0
    assert detected / faulty >= 0.8


@pytest.mark.parametrize('amount', ['35.000đ', '35,000 VND', '35000 đồng', '35 000 ₫'])
def test_lab9_reply_amount_formats(amount):
    trial = {'snapshot': {'refund_vnd': 35000},
             'events': [{'kind': 'reply', 'payload': {'text': f'Đã hoàn {amount} cho đơn O-202.'}}]}
    ctx = SimpleNamespace(output=trial)
    assert ReplyAmountCorrect().evaluate(ctx).value is True
    trial['snapshot']['refund_vnd'] = 20000
    assert ReplyAmountCorrect().evaluate(ctx).value is False


def test_lab9_reply_uses_final_reply_and_allows_no_monetary_claim():
    trial = {'snapshot': {'refund_vnd': 0}, 'events': [
        {'kind': 'reply', 'payload': {'text': 'Đã hoàn 35.000đ.'}},
        {'kind': 'reply', 'payload': {'text': 'Đơn chưa đủ điều kiện hoàn.'}},
    ]}
    assert ReplyAmountCorrect().evaluate(SimpleNamespace(output=trial)).value is True


def test_lab9_fm08_runs_through_harness(monkeypatch):
    variants.register()
    monkeypatch.setitem(SHAPES, 'm3_misreport', make_shape('m3_misreport', {'no_override', 'misreport'}))
    spec = load_spec()
    metric = next(m for m in spec['metrics'] if m['id'] == 'reply_amount_correct')
    assert metric['blocking'] and metric['kind'] == 'capability'
    report = run_eval('m3_misreport', spec)
    assert not report['evaluator_failures']
    item_id = next(i['item_id'] for i in load_items(Path(spec['eval_set'])) if i['claim_id'] == 'C-008')
    rows = [r for r in report['rows'] if r['item_id'] == item_id]
    assert len(rows) == 5
    assert all(r['refund_amount_correct'] and not r['reply_amount_correct'] for r in rows)
