#!/usr/bin/env python3
"""Anonymise rectangular regions of frame images in place (pixelate + blur).

Usage:
  python blur_frames.py --region X,Y,W,H [--region ...] [--preview OUT.jpg] IMAGE [IMAGE ...]

Regions are percentages of the image (0-100): X,Y is the top-left corner, W,H the size.
Example: --region 75,70,25,30 covers the bottom-right quarter-ish (a webcam overlay).
Percentages keep one region valid across frames of different sizes.

--preview writes the first image with the regions outlined in red instead of modifying
anything, so the user can confirm the area before it is applied to every frame.

Pixelation is irreversible once the file is overwritten, which is the point: apply it to
the temporary frame copies, never to a user's source file. Standard library only; needs
ffmpeg and ffprobe on PATH.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys


def parse_region(text):
    try:
        x, y, w, h = (float(v) for v in text.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError(f"region must be X,Y,W,H percentages, got {text!r}")
    if not (0 <= x < 100 and 0 <= y < 100 and 0 < w <= 100 and 0 < h <= 100):
        raise argparse.ArgumentTypeError(f"region out of range: {text!r}")
    return x, y, min(w, 100 - x), min(h, 100 - y)


def image_size(ffprobe, path):
    out = subprocess.run(
        [ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "json", path],
        capture_output=True, text=True, check=True,
    ).stdout
    s = json.loads(out)["streams"][0]
    return int(s["width"]), int(s["height"])


def to_pixels(region, iw, ih):
    x, y, w, h = region
    px, py = int(iw * x / 100), int(ih * y / 100)
    pw, ph = max(2, int(iw * w / 100)), max(2, int(ih * h / 100))
    return px, py, min(pw, iw - px), min(ph, ih - py)


def anonymise_filter(regions, iw, ih):
    chains, last = [], "0:v"
    for i, region in enumerate(regions):
        x, y, w, h = to_pixels(region, iw, ih)
        # Block size grows with the region, so large areas (faces) stay unrecognisable.
        block = max(16, min(w, h) // 8)
        small_w, small_h = max(1, w // block), max(1, h // block)
        chains.append(f"[{last}]split[b{i}][r{i}]")
        chains.append(
            f"[r{i}]crop={w}:{h}:{x}:{y},scale={small_w}:{small_h},"
            f"scale={w}:{h}:flags=neighbor,boxblur=2:1[p{i}]"
        )
        chains.append(f"[b{i}][p{i}]overlay={x}:{y}[o{i}]")
        last = f"o{i}"
    return ";".join(chains), f"[{last}]"


def outline_filter(regions, iw, ih):
    boxes = []
    for region in regions:
        x, y, w, h = to_pixels(region, iw, ih)
        boxes.append(f"drawbox=x={x}:y={y}:w={w}:h={h}:color=red@0.9:t=4")
    return ",".join(boxes)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--region", type=parse_region, action="append", required=True)
    ap.add_argument("--preview", help="write an outlined preview of the first image here and exit")
    ap.add_argument("images", nargs="+")
    args = ap.parse_args()

    ffmpeg, ffprobe = shutil.which("ffmpeg"), shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        sys.exit("ffmpeg/ffprobe not found on PATH.")

    if args.preview:
        if not os.path.isfile(args.images[0]):
            sys.exit(f"image not found: {args.images[0]}")
        iw, ih = image_size(ffprobe, args.images[0])
        subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", args.images[0],
                        "-vf", outline_filter(args.region, iw, ih), "-q:v", "2", args.preview], check=True)
        print(json.dumps({"preview": os.path.abspath(args.preview)}))
        return

    done, failed = [], []
    for path in args.images:
        if not os.path.isfile(path):
            failed.append({"path": path, "error": "file not found"})
            continue
        root, ext = os.path.splitext(path)
        tmp = f"{root}.anon-tmp{ext}"
        try:
            iw, ih = image_size(ffprobe, path)
            graph, out = anonymise_filter(args.region, iw, ih)
            subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", path, "-filter_complex", graph,
                            "-map", out, "-q:v", "2", tmp], check=True)
            os.replace(tmp, path)
            done.append(path)
        except (subprocess.CalledProcessError, KeyError, IndexError, ValueError) as exc:
            failed.append({"path": path, "error": str(exc)})
            if os.path.exists(tmp):
                os.remove(tmp)
    print(json.dumps({"anonymised": len(done), "failed": failed}, indent=2))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
