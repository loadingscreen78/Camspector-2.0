import copy

import pytest

from camspector import contract as C
from camspector.baseline import baseline_prediction, even_highlights


def _valid(duration=100.0):
    return {
        C.KEY_VIDEO_ID: "P01_01",
        C.KEY_LABEL: "cooking",
        C.KEY_ACTIONS: [{C.ACTION_VERB: "open", C.ACTION_NOUN: "door",
                         C.ACTION_START: 1.0, C.ACTION_END: 2.0}],
        C.KEY_HIGHLIGHTS: [{C.HL_START: 10.0, C.HL_END: 15.0, C.HL_IMPORTANCE: 0.9},
                           {C.HL_START: 20.0, C.HL_END: 29.0, C.HL_IMPORTANCE: 0.3}],
    }


def test_valid_passes():
    assert C.check_output(_valid(), 100.0) == []


@pytest.mark.parametrize("mutate,needle", [
    (lambda o: o.pop(C.KEY_LABEL), "top-level"),
    (lambda o: o.__setitem__("extra", 1), "top-level"),
    (lambda o: o[C.KEY_HIGHLIGHTS][0].__setitem__(C.HL_END, 9.0), "start must be < end"),
    (lambda o: o[C.KEY_HIGHLIGHTS][1].__setitem__(C.HL_START, 12.0), "overlaps"),
    (lambda o: o[C.KEY_HIGHLIGHTS].reverse(), "out of order"),
    (lambda o: o[C.KEY_HIGHLIGHTS][0].__setitem__(C.HL_IMPORTANCE, 1.5), "importance"),
    (lambda o: o[C.KEY_HIGHLIGHTS][0].__setitem__(C.HL_IMPORTANCE, True), "importance"),
    (lambda o: o[C.KEY_HIGHLIGHTS][1].__setitem__(C.HL_END, 40.0), "exceeds budget"),
    (lambda o: o[C.KEY_HIGHLIGHTS][1].__setitem__(C.HL_END, 101.0), "outside"),
    (lambda o: o[C.KEY_ACTIONS][0].__setitem__(C.ACTION_START, -1.0), "outside"),
    (lambda o: o[C.KEY_ACTIONS][0].__setitem__(C.ACTION_END, float("nan")), "finite"),
    (lambda o: o[C.KEY_ACTIONS][0].__setitem__(C.ACTION_VERB, 3), "string"),
])
def test_violations_detected(mutate, needle):
    o = copy.deepcopy(_valid())
    mutate(o)
    errs = C.check_output(o, 100.0)
    assert any(needle in e for e in errs), errs


def test_supported_classes_enforced():
    cs = C.ClassSet(verbs={"open"}, nouns={"door"}, labels={"cooking"})
    assert C.check_output(_valid(), 100.0, cs) == []
    o = _valid()
    o[C.KEY_ACTIONS][0][C.ACTION_NOUN] = "robbery"
    assert any("unsupported pair" in e for e in C.check_output(o, 100.0, cs))
    o = _valid()
    o[C.KEY_LABEL] = "theft"
    assert any("unsupported label" in e for e in C.check_output(o, 100.0, cs))


@pytest.mark.parametrize("duration", [0.0, 0.5, 7.3, 120.0, 333.33, 600.0, 3600.0])
def test_baseline_always_valid(duration):
    p = baseline_prediction("vid", duration)
    assert C.check_output(p.to_json(), duration) == []
    total = sum(h.end - h.start for h in p.highlights)
    assert total <= C.highlight_budget_s(duration) + 1e-9
    if duration >= 60:
        assert total >= 0.14 * duration  # fills close to the 14.5% target


def test_sanitize_clips_merges_and_trims():
    d = 100.0
    raw = [C.Highlight(-5, 5, 2.0), C.Highlight(3, 8, 0.4), C.Highlight(50, 90, 0.1),
           C.Highlight(95, 120, 0.2)]
    out = C.sanitize_highlights(raw, d)
    assert C.check_output({C.KEY_VIDEO_ID: "x", C.KEY_LABEL: "y", C.KEY_ACTIONS: [],
                           C.KEY_HIGHLIGHTS: [h.to_json() for h in out]}, d) == []
    assert out[0].start == 0 and out[0].importance == 1.0


def test_even_highlights_sorted_nonoverlapping():
    hs = even_highlights(480.0)
    assert all(a.end <= b.start for a, b in zip(hs, hs[1:]))


def test_video_id_rule():
    assert C.video_id_from_path("/x/y z/P01_01.mp4") == "P01_01"
