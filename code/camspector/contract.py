"""Output contract for Track 4 -- the ONLY place schema details live.

Every constant below is PROVISIONAL - verify against kit. It is built from the
illustrative schema on the challenge slides. When the student kit arrives
(TEAM_README.md, validate.py, examples/), update this file and nothing else.
No other module may hard-code key names, budgets or ranges.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

# ---------------------------------------------------------------------------
# Schema constants
# ---------------------------------------------------------------------------
KEY_VIDEO_ID = "video_id"          # PROVISIONAL - verify against kit
KEY_LABEL = "label"                # PROVISIONAL - verify against kit
KEY_ACTIONS = "actions"            # PROVISIONAL - verify against kit
KEY_HIGHLIGHTS = "highlights"      # PROVISIONAL - verify against kit
TOP_LEVEL_KEYS = (KEY_VIDEO_ID, KEY_LABEL, KEY_ACTIONS, KEY_HIGHLIGHTS)

ACTION_VERB = "verb"               # PROVISIONAL - verify against kit
ACTION_NOUN = "noun"               # PROVISIONAL - verify against kit
ACTION_START = "start"             # PROVISIONAL - verify against kit
ACTION_END = "end"                 # PROVISIONAL - verify against kit
# Whether actions carry a confidence score decides the mAP strategy.
ACTION_SCORE_KEY: str | None = None  # PROVISIONAL - verify against kit (e.g. "score")

HL_START = "start"                 # PROVISIONAL - verify against kit
HL_END = "end"                     # PROVISIONAL - verify against kit
HL_IMPORTANCE = "importance"       # PROVISIONAL - verify against kit
IMPORTANCE_RANGE = (0.0, 1.0)      # PROVISIONAL - verify against kit

HIGHLIGHT_BUDGET_FRAC = 0.15       # PROVISIONAL - verify against kit (hard cap we enforce)
HIGHLIGHT_TARGET_FRAC = 0.145      # our fill target, kept below the cap
MIN_HIGHLIGHT_LEN_S = 0.0          # PROVISIONAL - verify against kit (min segment length)
ALLOW_EMPTY_ACTIONS = True         # PROVISIONAL - verify against kit
TIME_DECIMALS = 3                  # PROVISIONAL - verify against kit (rounding of times)

DEFAULT_LABEL = "unknown"          # PROVISIONAL - replaced by most frequent category from kit


def video_id_from_path(path: str | Path) -> str:
    """PROVISIONAL - verify against kit: video_id = file stem (e.g. P01_01.mp4 -> P01_01)."""
    return Path(path).stem


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class Action:
    verb: str
    noun: str
    start: float
    end: float
    score: float | None = None

    def to_json(self) -> dict:
        d = {
            ACTION_VERB: self.verb,
            ACTION_NOUN: self.noun,
            ACTION_START: _r(self.start),
            ACTION_END: _r(self.end),
        }
        if ACTION_SCORE_KEY is not None:
            d[ACTION_SCORE_KEY] = float(self.score if self.score is not None else 1.0)
        return d


@dataclass
class Highlight:
    start: float
    end: float
    importance: float

    def to_json(self) -> dict:
        return {
            HL_START: _r(self.start),
            HL_END: _r(self.end),
            HL_IMPORTANCE: round(float(self.importance), 6),
        }


@dataclass
class Prediction:
    video_id: str
    label: str
    duration: float
    actions: list[Action] = field(default_factory=list)
    highlights: list[Highlight] = field(default_factory=list)

    def to_json(self) -> dict:
        return {
            KEY_VIDEO_ID: self.video_id,
            KEY_LABEL: self.label,
            KEY_ACTIONS: [a.to_json() for a in self.actions],
            KEY_HIGHLIGHTS: [h.to_json() for h in self.highlights],
        }


def _r(x: float) -> float:
    return round(float(x), TIME_DECIMALS)


def highlight_budget_s(duration: float) -> float:
    """PROVISIONAL - verify against kit: budget = 15% of video duration."""
    return HIGHLIGHT_BUDGET_FRAC * float(duration)


# ---------------------------------------------------------------------------
# Supported classes
# ---------------------------------------------------------------------------
@dataclass
class ClassSet:
    """Supported verbs/nouns/labels. Empty sets mean 'unknown' (kit not loaded)."""
    verbs: set[str] = field(default_factory=set)
    nouns: set[str] = field(default_factory=set)
    pairs: set[tuple[str, str]] = field(default_factory=set)
    labels: set[str] = field(default_factory=set)

    @classmethod
    def load(cls, path: str | Path | None) -> "ClassSet":
        """PROVISIONAL - verify against kit: format of supported_classes.json is unknown.
        Accepts {"verbs": [...], "nouns": [...], "pairs": [[v, n], ...], "labels": [...]}."""
        if path is None or not Path(path).exists():
            return cls()
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            verbs=set(raw.get("verbs", [])),
            nouns=set(raw.get("nouns", [])),
            pairs={tuple(p) for p in raw.get("pairs", [])},
            labels=set(raw.get("labels", raw.get("categories", []))),
        )

    def allows_action(self, verb: str, noun: str) -> bool:
        if self.pairs:
            return (verb, noun) in self.pairs
        ok_v = not self.verbs or verb in self.verbs
        ok_n = not self.nouns or noun in self.nouns
        return ok_v and ok_n

    def allows_label(self, label: str) -> bool:
        return not self.labels or label in self.labels


# ---------------------------------------------------------------------------
# Validation (mirrors what we believe validate.py checks)
# ---------------------------------------------------------------------------
def check_output(obj: dict, duration: float, classes: ClassSet | None = None,
                 eps: float = 1e-3) -> list[str]:
    """Return a list of contract violations (empty list == valid)."""
    errs: list[str] = []
    classes = classes or ClassSet()
    if set(obj.keys()) != set(TOP_LEVEL_KEYS):
        errs.append(f"top-level keys {sorted(obj)} != {sorted(TOP_LEVEL_KEYS)}")
        return errs
    if not isinstance(obj[KEY_VIDEO_ID], str) or not obj[KEY_VIDEO_ID]:
        errs.append("video_id must be a non-empty string")
    if not isinstance(obj[KEY_LABEL], str):
        errs.append("label must be a string")
    elif not classes.allows_label(obj[KEY_LABEL]):
        errs.append(f"unsupported label {obj[KEY_LABEL]!r}")

    acts = obj[KEY_ACTIONS]
    if not isinstance(acts, list):
        errs.append("actions must be a list")
        acts = []
    if not acts and not ALLOW_EMPTY_ACTIONS:
        errs.append("actions must be non-empty")
    for i, a in enumerate(acts):
        errs += _check_interval(a, ACTION_START, ACTION_END, duration, f"actions[{i}]", eps)
        for k in (ACTION_VERB, ACTION_NOUN):
            if not isinstance(a.get(k), str):
                errs.append(f"actions[{i}].{k} must be a string")
        if isinstance(a.get(ACTION_VERB), str) and isinstance(a.get(ACTION_NOUN), str):
            if not classes.allows_action(a[ACTION_VERB], a[ACTION_NOUN]):
                errs.append(f"actions[{i}] unsupported pair {a[ACTION_VERB]}/{a[ACTION_NOUN]}")

    hls = obj[KEY_HIGHLIGHTS]
    if not isinstance(hls, list):
        return errs + ["highlights must be a list"]
    total, prev_end = 0.0, -math.inf
    lo, hi = IMPORTANCE_RANGE
    for i, h in enumerate(hls):
        e = _check_interval(h, HL_START, HL_END, duration, f"highlights[{i}]", eps)
        errs += e
        if e:
            continue
        if h[HL_START] < prev_end - eps:
            errs.append(f"highlights[{i}] overlaps or is out of order")
        prev_end = h[HL_END]
        total += h[HL_END] - h[HL_START]
        if h[HL_END] - h[HL_START] < MIN_HIGHLIGHT_LEN_S - eps:
            errs.append(f"highlights[{i}] shorter than {MIN_HIGHLIGHT_LEN_S}s")
        imp = h.get(HL_IMPORTANCE)
        if not _is_num(imp) or not (lo <= imp <= hi):
            errs.append(f"highlights[{i}].importance must be a number in [{lo}, {hi}]")
    if total > highlight_budget_s(duration) + eps:
        errs.append(f"highlight total {total:.3f}s exceeds budget {highlight_budget_s(duration):.3f}s")
    return errs


def _is_num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _check_interval(d: dict, ks: str, ke: str, duration: float, name: str, eps: float) -> list[str]:
    if not isinstance(d, dict):
        return [f"{name} must be an object"]
    s, e = d.get(ks), d.get(ke)
    if not (_is_num(s) and _is_num(e)):
        return [f"{name} start/end must be finite numbers"]
    out = []
    if s < -eps or e > duration + eps:
        out.append(f"{name} [{s}, {e}] outside [0, {duration}]")
    if not s < e:
        out.append(f"{name} start must be < end")
    return out


def write_json(pred: Prediction, path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(pred.to_json(), indent=2), encoding="utf-8")
    tmp.replace(path)  # atomic: never leave a half-written JSON


def sanitize_highlights(hls: Iterable[Highlight], duration: float) -> list[Highlight]:
    """Clip to [0, duration], sort, merge overlaps, trim to budget, clamp importance."""
    lo, hi = IMPORTANCE_RANGE
    items = sorted(
        (Highlight(max(0.0, h.start), min(duration, h.end), min(hi, max(lo, h.importance)))
         for h in hls),
        key=lambda h: h.start,
    )
    merged: list[Highlight] = []
    for h in items:
        if h.end - h.start <= 0:
            continue
        if merged and h.start <= merged[-1].end:
            m = merged[-1]
            m.end = max(m.end, h.end)
            m.importance = max(m.importance, h.importance)
        else:
            merged.append(h)
    # round first (as written), then trim the tail so rounded totals fit the budget
    budget = highlight_budget_s(duration) - 10 ** (-TIME_DECIMALS)
    out, used = [], 0.0
    for h in merged:
        s, e = _r(h.start), _r(h.end)
        if e - s <= 0:
            continue
        room = budget - used
        if room <= 0:
            break
        if e - s > room:
            e = _r(s + room - 10 ** (-TIME_DECIMALS))
            if e <= s:
                break
        out.append(Highlight(s, e, h.importance))
        used += e - s
    return out
