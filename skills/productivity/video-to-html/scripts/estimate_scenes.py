#!/usr/bin/env python3
"""Estimate how visually busy a video is, to size the frame budget before extraction.

Usage:
  python estimate_scenes.py VIDEO [--start T] [--end T] [--width 1024] [--json OUT.json]

Decodes a downscaled, low-fps copy of the video with ffmpeg, scores every sampled
frame for scene change, and reports how many scene changes exist at three
sensitivities, where they cluster, and three suggested frame budgets with a rough
image-token cost. Standard library only; needs ffmpeg and ffprobe on PATH.
"""
import argparse
import json
import math
import re
import shutil
import subprocess
import sys

THRESHOLDS = {"sensitive": 0.15, "standard": 0.30, "major": 0.45}
MIN_GAP_S = 2.0  # cuts closer than this collapse into one (flashes, transitions)


def parse_time(value):
    if value is None:
        return None
    parts = [float(p) for p in str(value).split(":")]
    seconds = 0.0
    for p in parts:
        seconds = seconds * 60 + p
    return seconds


def fmt(seconds):
    seconds = int(round(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def probe_duration(ffprobe, video):
    out = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "json", video],
        capture_output=True, text=True, check=True,
    ).stdout
    return float(json.loads(out)["format"]["duration"])


def scene_scores(ffmpeg, video, start, end, fps):
    cmd = [ffmpeg, "-hide_banner", "-nostats", "-loglevel", "error"]
    if start:
        cmd += ["-ss", str(start)]
    if end:
        cmd += ["-to", str(end)]
    vf = f"fps={fps},scale=320:-2,select='gte(scene\\,0)',metadata=print:key=lavfi.scene_score:file=-"
    cmd += ["-i", video, "-an", "-sn", "-vf", vf, "-f", "null", "-"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(f"ffmpeg failed: {proc.stderr.strip()[-800:]}")
    scores, t = [], None
    for line in proc.stdout.splitlines():
        m = re.search(r"pts_time:([\d.]+)", line)
        if m:
            t = float(m.group(1)) + (start or 0)
            continue
        m = re.search(r"lavfi\.scene_score=([\d.]+)", line)
        if m and t is not None:
            scores.append((t, float(m.group(1))))
    return scores


def cuts_at(scores, threshold):
    cuts = []
    for t, s in scores:
        if s >= threshold and (not cuts or t - cuts[-1] >= MIN_GAP_S):
            cuts.append(t)
    return cuts


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video")
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--width", type=int, default=1024, help="frame width planned for extraction (token estimate)")
    ap.add_argument("--json", help="also write the result to this file")
    args = ap.parse_args()

    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        sys.exit("ffmpeg/ffprobe not found on PATH. Run the watch skill's setup.py first.")

    total = probe_duration(ffprobe, args.video)
    start = parse_time(args.start) or 0.0
    end = min(parse_time(args.end) or total, total)
    if start >= end:
        sys.exit(f"--start ({fmt(start)}) must be before --end/video end ({fmt(end)})")
    span = max(1.0, end - start)
    fps = 2 if span <= 1200 else 1 if span <= 3600 else 0.5

    scores = scene_scores(ffmpeg, args.video, start or None, end if end < total else None, fps)
    counts = {name: cuts_at(scores, th) for name, th in THRESHOLDS.items()}
    minutes = span / 60

    light = clamp(len(counts["major"]) + 1, 6, 40)
    balanced = clamp(len(counts["standard"]) + 1, max(light, 10), 100)
    thorough = clamp(len(counts["sensitive"]) + 1, max(balanced, 15), 200)
    tokens_per_frame = round(args.width * (args.width * 9 / 16) / 750)

    # Scene changes per minute at the standard threshold, to show where the action is.
    buckets = [0] * max(1, math.ceil(minutes))
    for t in counts["standard"]:
        buckets[min(len(buckets) - 1, int((t - start) // 60))] += 1
    peak = max(buckets) or 1
    bars = " ▁▂▃▄▅▆▇█"
    sparkline = "".join(bars[min(8, math.ceil(b / peak * 8))] for b in buckets)
    busiest = sorted(range(len(buckets)), key=lambda i: buckets[i], reverse=True)[:3]

    result = {
        "duration": fmt(span),
        "duration_seconds": round(span, 1),
        "range": {"start": fmt(start), "end": fmt(end)},
        "sampled_fps": fps,
        "scene_changes": {name: len(c) for name, c in counts.items()},
        "scene_changes_per_minute": round(len(counts["standard"]) / minutes, 2),
        "timeline_per_minute": buckets,
        "timeline_sparkline": sparkline,
        "busiest_minutes": [f"{fmt(start + i * 60)}-{fmt(min(end, start + (i + 1) * 60))}" for i in busiest if buckets[i]],
        "budgets": {
            "light": {"max_frames": light, "approx_image_tokens": light * tokens_per_frame},
            "balanced": {"max_frames": balanced, "approx_image_tokens": balanced * tokens_per_frame},
            "thorough": {"max_frames": thorough, "approx_image_tokens": thorough * tokens_per_frame},
        },
        "frame_width": args.width,
        "static_video": len(counts["standard"]) < max(3, minutes * 0.3),
    }
    text = json.dumps(result, indent=2, ensure_ascii=False)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            fh.write(text)
    sys.stdout.reconfigure(encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
