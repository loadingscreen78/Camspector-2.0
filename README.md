# CAMSPECTOR: Track 4, Action-Aware Video Summarization

Samsung PRISM XR Hackathon 2026, Track 4 ("Meaningful Highlights from Egocentric Video").
Input: one first-person MP4 (2–10 min). Output: one JSON with verb–noun actions, highlight
ranges (~15% of the original footage) and a video-level label.

> **Status: Phase 0.5 (kit-independent setup).** The student kit has not been audited yet, so the
> output schema in `code/camspector/contract.py` is **PROVISIONAL** and is built from the
> challenge slides. The model path is not built; `run.sh` currently writes a valid
> **baseline** JSON (evenly spaced highlights, no actions). No metrics have been computed yet.

## Run

```bash
./run.sh <video.mp4> <out.json>          # logs go to stderr
code/scripts/run_all.sh <video_dir> outputs/
```
Set `CAMSPECTOR_PYTHON` to choose the interpreter (default: `python`).

## Setup

```bash
# Python 3.11
pip install torch==2.14.1 torchvision==0.29.1 --index-url https://download.pytorch.org/whl/cu126   # or .../whl/cpu
pip install -r requirements.txt
python code/scripts/make_synthetic_videos.py data/synthetic
PYTHONPATH=code python -m pytest code/tests -q
```
One-command setup + GPU benchmark on another machine: see [HANDOFF.md](HANDOFF.md).

## Layout

| Path | Purpose |
|---|---|
| `run.sh` | Entry point: `run.sh <video.mp4> <out.json>` |
| `code/camspector/contract.py` | **Only** place schema details live (keys, budget, ranges) |
| `code/camspector/video_io.py` | PTS-based decoding (VFR, rotation, corrupt or truncated files) |
| `code/camspector/pipeline.py` | Orchestration. Any failure falls back to a valid baseline JSON |
| `code/scripts/` | Synthetic videos, EPIC stats, encoder benchmark, GPU check |
| `code/tests/` | pytest suite: contract rules, video edge cases, `run.sh` behaviour |
| `docs/` | EPIC stats, feature-parity research, storage plan |
| `experiments/` | Benchmark and results files (real measurements only) |

Videos, annotations, features, weights and caches are git-ignored (dataset licences).

## Docs

- [docs/EPIC_STATS.md](docs/EPIC_STATS.md): EPIC-100 annotation statistics for the coverage strategy
- [docs/FEATURES_PARITY.md](docs/FEATURES_PARITY.md): public SlowFast features and the proposed parity test
- [docs/STORAGE_PLAN.md](docs/STORAGE_PLAN.md): download → extract → delete loop, with estimates

## Licences

EPIC-KITCHENS-100 annotations and models are CC BY-NC 4.0; they are not redistributed in
this repo. Code: to be decided by the team.
