"""Phase-1 baseline outputs. Needs no model and cannot fail for a valid duration."""
from __future__ import annotations

from . import contract as C


def even_highlights(duration: float, n: int | None = None,
                    frac: float = C.HIGHLIGHT_TARGET_FRAC) -> list[C.Highlight]:
    """Evenly spaced windows totalling `frac` of duration, importance 0.5."""
    if duration <= 0:
        return []
    total = frac * duration
    n = n or max(1, min(10, int(duration // 30)))  # ~1 window per 30 s, max 10
    seg = total / n
    gap = (duration - total) / n
    out = []
    for i in range(n):
        s = gap / 2 + i * (seg + gap)
        out.append(C.Highlight(s, s + seg, 0.5))
    return C.sanitize_highlights(out, duration)


def baseline_prediction(video_id: str, duration: float,
                        label: str = C.DEFAULT_LABEL) -> C.Prediction:
    return C.Prediction(
        video_id=video_id,
        label=label,
        duration=duration,
        actions=[],  # PROVISIONAL: assumes empty actions are allowed (C.ALLOW_EMPTY_ACTIONS)
        highlights=even_highlights(duration),
    )
