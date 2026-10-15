# -*- coding: utf-8 -*-
"""measure_ref.py — 参照音声の候補を測る（途切れ・先頭の無音・発話長・F0）。

    uv run --with numpy python measure_ref.py ref_*.wav

ffmpeg で 16kHz モノラルに落とし、0.2秒フレームの RMS が -45dB 未満を無音とみなす。
採用の目安（references/reference-voice.md）:
  途切れ 0 箇所（必須） / 先頭の無音 0 秒 / 発話 3〜5秒 / F0 が狙った性別の帯域
「○ 候補」の判定は途切れ・先頭・発話長だけで行う。F0 は数値を見て確かめる。
声質の良し悪しは測れないので、数値で絞った候補は人が聴いて決める。
"""
from __future__ import annotations

import argparse
import glob
import shutil
import subprocess
import sys

import numpy as np

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

SR = 16000
FRAME_SEC = 0.2
SILENCE_DB = -45.0
GAP_SEC = 0.4


def load(path: str) -> np.ndarray:
    pcm = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"],
        check=True, capture_output=True,
    ).stdout
    return np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0


def frame_db(x: np.ndarray) -> np.ndarray:
    n = int(SR * FRAME_SEC)
    frames = x[: len(x) // n * n].reshape(-1, n)
    rms = np.sqrt(np.mean(frames ** 2, axis=1))
    return 20 * np.log10(np.maximum(rms, 1e-10))


def silence_stats(voiced: np.ndarray) -> dict:
    idx = np.flatnonzero(voiced)
    if idx.size == 0:
        return {"lead": None, "speech": 0.0, "gaps": []}
    first, last = idx[0], idx[-1]
    gaps, run = [], 0
    for v in voiced[first : last + 1]:
        if v:
            if run * FRAME_SEC >= GAP_SEC:
                gaps.append(round(run * FRAME_SEC, 1))
            run = 0
        else:
            run += 1
    return {
        "lead": round(first * FRAME_SEC, 1),
        "speech": round((last - first + 1) * FRAME_SEC, 1),
        "gaps": gaps,
    }


def f0_median(x: np.ndarray, voiced: np.ndarray) -> float | None:
    """有声フレーム（40ms 窓）の自己相関ピークから F0 を出し、中央値を返す。"""
    win, hop = int(SR * 0.04), int(SR * 0.01)
    lo, hi = SR // 400, SR // 60          # 60〜400Hz を探す
    vframe = int(SR * FRAME_SEC)
    f0s = []
    for start in range(0, len(x) - win, hop):
        if not voiced[min(start // vframe, len(voiced) - 1)]:
            continue
        w = x[start : start + win] - np.mean(x[start : start + win])
        if np.sum(w ** 2) < 1e-6:
            continue
        ac = np.correlate(w, w, mode="full")[win - 1 :]
        if ac[0] <= 0:
            continue
        lag = lo + int(np.argmax(ac[lo:hi]))
        if ac[lag] / ac[0] > 0.5:          # 周期性の弱いフレーム（無声音）は捨てる
            f0s.append(SR / lag)
    return round(float(np.median(f0s)), 1) if f0s else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", help="測る音声（ワイルドカード可）")
    args = ap.parse_args()

    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg が見つかりません。インストールして PATH を通してください。")

    paths = [p for pat in args.files for p in (sorted(glob.glob(pat)) or [pat])]
    print(f"{'file':<32} {'途切れ':>6} {'先頭':>6} {'発話':>6} {'F0':>7}  判定")
    for path in paths:
        try:
            x = load(path)
        except subprocess.CalledProcessError as e:
            print(f"{path:<32} 読めません: {e.stderr.decode(errors='replace').strip()}")
            continue
        voiced = frame_db(x) >= SILENCE_DB
        s = silence_stats(voiced)
        f0 = f0_median(x, voiced)
        ok = s["lead"] == 0 and not s["gaps"] and 3.0 <= s["speech"] <= 5.0
        lead = "-" if s["lead"] is None else f"{s['lead']}s"
        gaps = str(len(s["gaps"])) + (f" {s['gaps']}" if s["gaps"] else "")
        print(f"{path:<32} {gaps:>6} {lead:>6} {s['speech']:>5}s {str(f0 or '-'):>6}Hz  "
              + ("○ 候補" if ok else "×"))
    print("\n○ 判定は途切れ・先頭・発話長のみ。F0 は目安（成人男性 85〜180Hz / 成人女性 165〜255Hz）と見比べる")
    return 0


if __name__ == "__main__":
    sys.exit(main())
