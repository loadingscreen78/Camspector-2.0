"""Entry point: python -m camspector.pipeline --video X.mp4 --out X.json

Always writes a valid JSON: any failure in the model path falls back to the baseline.
Logs go to stderr only.
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
import traceback
from pathlib import Path

from . import contract as C
from .baseline import baseline_prediction
from .video_io import probe

log = logging.getLogger("camspector")


def run_model(video: Path, duration: float) -> C.Prediction:
    """Model path (Phases 3-9). Not implemented yet -> raises, triggering the fallback."""
    raise NotImplementedError("model pipeline not built yet (Phase 3+)")


def _safe_duration(video: Path) -> float:
    try:
        return probe(video, scan=True).duration
    except Exception as e:  # unreadable file: still write a schema-valid JSON
        log.error("probe failed for %s: %s", video, e)
        return 0.0


def process(video: Path, out: Path, use_model: bool = True) -> dict:
    t0 = time.perf_counter()
    vid = C.video_id_from_path(video)
    duration = _safe_duration(video)
    pred = None
    if use_model:
        try:
            pred = run_model(video, duration)
            errs = C.check_output(pred.to_json(), duration)
            if errs:
                raise ValueError(f"model output invalid: {errs[:3]}")
        except NotImplementedError as e:
            log.info("fallback: %s", e)
            pred = None
        except Exception:
            log.error("model path failed, using baseline:\n%s", traceback.format_exc())
            pred = None
    if pred is None:
        pred = baseline_prediction(vid, duration)
    C.write_json(pred, out)
    dt = time.perf_counter() - t0
    log.info("wrote %s (duration=%.2fs, %d actions, %d highlights) in %.2fs",
             out, duration, len(pred.actions), len(pred.highlights), dt)
    return {"video_id": vid, "duration": duration, "seconds": dt}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--baseline-only", action="store_true")
    a = ap.parse_args(argv)
    logging.basicConfig(stream=sys.stderr, level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    try:
        process(a.video, a.out, use_model=not a.baseline_only)
    except Exception:  # last resort: still emit a valid JSON
        log.critical("unexpected failure:\n%s", traceback.format_exc())
        C.write_json(baseline_prediction(C.video_id_from_path(a.video), 0.0), a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
