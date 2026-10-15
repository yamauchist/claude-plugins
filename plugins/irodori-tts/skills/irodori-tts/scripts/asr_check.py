# -*- coding: utf-8 -*-
"""asr_check.py — 合成した音声が本文どおり喋っているか、文字起こしで確かめる。

    uv run --python 3.11 --with faster-whisper --with pykakasi python asr_check.py pairs.tsv
    ... asr_check.py pairs.tsv --model large-v3 --device cuda --json result.json

pairs.tsv は「音声パス<TAB>合成に渡した本文」を1行1本で並べたもの（# で始まる行は無視）。
本文は元の表記ではなく、読み替えや記号だけの文の置換を済ませた「実際に送った文字列」にする。

本文と転写をひらがなに直して編集距離を取り（かな CER）、外れた行を挙げる。
判定は目安であって合否ではない。Whisper は崩れた音声をもっともらしい日本語へ
直すことがあるので、挙がった行は聴いて判断する。音声が見つからない行も要確認に数える。
終了コードは --strict のときだけ 1。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

# Windows の既定は cp932 で、日本語や「▶」を書くと落ちる
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

# かなに直したうえでこれだけ食い違ったら要確認。表記ゆれは 0.2 に収まる
CER_THRESHOLD = 0.20
# Whisper が読み取りに苦労した目安。破綻の傍証になる
LOGPROB_THRESHOLD = -0.8

# かな・カナ・漢字（々〆 を含む）・英数字以外を落とす。句読点・記号・絵文字は発話にならない
_NON_SPEECH = re.compile(r"[^぀-ヿ々〆一-鿿ｦ-ﾟa-zA-Z0-9]")


def build_kana():
    import pykakasi
    kks = pykakasi.kakasi()

    def kana(s: str) -> str:
        s = unicodedata.normalize("NFKC", s)
        s = _NON_SPEECH.sub("", s)
        s = "".join(item["hira"] for item in kks.convert(s))
        s = _NON_SPEECH.sub("", s)    # 変換結果に残った記号も落とす
        return s.replace("ー", "")   # 長音は転写側で揺れるので落とす

    return kana


def cer(ref: str, hyp: str) -> float:
    """編集距離を参照長で割る。ref が空なら hyp も空のときだけ 0。"""
    if not ref:
        return 0.0 if not hyp else 1.0
    prev = list(range(len(hyp) + 1))
    for i, rc in enumerate(ref, 1):
        cur = [i]
        for j, hc in enumerate(hyp, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (rc != hc)))
        prev = cur
    return prev[-1] / len(ref)


def read_pairs(path: Path) -> list[tuple[Path, str]]:
    pairs = []
    for n, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip() or line.startswith("#"):
            continue
        if "\t" not in line:
            sys.exit(f"{path}:{n}: タブ区切りになっていません: {line}")
        wav, text = line.split("\t", 1)
        pairs.append(((path.parent / wav).resolve() if not Path(wav).is_absolute() else Path(wav), text))
    return pairs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pairs", type=Path, help="音声パス<TAB>本文 の TSV（相対パスは TSV の場所から）")
    ap.add_argument("--model", default="medium", help="tiny/base/small/medium/large-v3")
    ap.add_argument("--device", default="cpu", help="cpu / cuda")
    ap.add_argument("--cer", type=float, default=CER_THRESHOLD)
    ap.add_argument("--json", type=Path, help="全行の結果を書き出す")
    ap.add_argument("--strict", action="store_true", help="要確認があれば終了コード 1")
    args = ap.parse_args()

    from faster_whisper import WhisperModel

    pairs = read_pairs(args.pairs)
    kana = build_kana()
    print(f"▶ Whisper {args.model} ({args.device}) を読み込み中…")
    model = WhisperModel(args.model, device=args.device,
                         compute_type="float16" if args.device == "cuda" else "int8")

    rows, flagged = [], []
    for wav, text in pairs:
        if not wav.exists():
            row = {"wav": str(wav), "text": text, "asr": "（音声ファイルが見つからない）",
                   "kana_cer": None, "avg_logprob": None, "missing": True}
            rows.append(row)
            flagged.append(row)
            print(f"  ✗ 見つかりません: {wav}")
            continue
        segments, _ = model.transcribe(str(wav), language="ja", beam_size=5,
                                       condition_on_previous_text=False)
        segments = list(segments)
        hyp = "".join(s.text for s in segments).strip()
        logp = (sum(s.avg_logprob for s in segments) / len(segments)) if segments else -9.0
        row = {
            "wav": str(wav), "text": text, "asr": hyp,
            "kana_cer": round(cer(kana(text), kana(hyp)), 3),
            "avg_logprob": round(logp, 3),
        }
        rows.append(row)
        bad = row["kana_cer"] > args.cer or row["avg_logprob"] < LOGPROB_THRESHOLD
        if bad:
            flagged.append(row)
        print(f"  {'⚠' if bad else '✓'} {wav.name}  CER {row['kana_cer']:.2f}  logP {row['avg_logprob']:.2f}")

    print(f"\n{len(rows)} 本中 {len(flagged)} 本が要確認（かなCER > {args.cer} または logP < {LOGPROB_THRESHOLD}、"
          "または音声が見つからない）")
    for r in sorted(flagged, key=lambda x: -(x["kana_cer"] if x["kana_cer"] is not None else 9)):
        if r.get("missing"):
            print(f"\n  {Path(r['wav']).name}  音声ファイルが見つからない")
        else:
            print(f"\n  {Path(r['wav']).name}  かなCER {r['kana_cer']:.2f}  logP {r['avg_logprob']:.2f}")
        print(f"    本文: {r['text']}")
        if not r.get("missing"):
            print(f"    転写: {r['asr']}")
    if flagged:
        print("\n挙がった行は聴いて判断すること（転写の揺れ・Whisper の補正で誤検出もある）。")

    if args.json:
        args.json.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return 1 if (args.strict and flagged) else 0


if __name__ == "__main__":
    sys.exit(main())
