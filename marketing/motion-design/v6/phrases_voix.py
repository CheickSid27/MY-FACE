# -*- coding: utf-8 -*-
"""Repere les phrases dans les voix des scenarios (scenarios/voix/S*.wav) par les silences.

    python marketing/motion-design/v6/phrases_voix.py      -> v6/phrases.json + affichage
"""

import json
import wave
from pathlib import Path

import numpy as np

ICI = Path(__file__).resolve().parent
VOIX = ICI.parent / "scenarios" / "voix"


def lire(chemin):
    with wave.open(str(chemin)) as w:
        sr, n, c = w.getframerate(), w.getnframes(), w.getnchannels()
        x = np.frombuffer(w.readframes(n), np.int16).astype(np.float32) / 32768
    if c > 1:
        x = x.reshape(-1, c).mean(1)
    return x, sr


def segments(x, sr, fen=0.02, seuil_db=-38, silence_min=0.32):
    """-> [(debut, fin)] des passages parles separes par >= silence_min de silence."""
    k = int(sr * fen)
    e = np.sqrt(np.mean(x[: len(x) // k * k].reshape(-1, k) ** 2, 1) + 1e-12)
    parle = 20 * np.log10(e) > seuil_db
    out, debut, calme = [], None, 0
    for i, p in enumerate(parle):
        if p:
            if debut is None:
                debut = i
            calme = 0
        elif debut is not None:
            calme += 1
            if calme * fen >= silence_min:
                out.append((debut * fen, (i - calme + 1) * fen))
                debut, calme = None, 0
    if debut is not None:
        out.append((debut * fen, len(parle) * fen))
    return [(round(a, 2), round(b, 2)) for a, b in out]


def main():
    res = {}
    for f in sorted(VOIX.glob("S*.wav")):
        x, sr = lire(f)
        s = segments(x, sr)
        res[f.stem] = {"duree": round(len(x) / sr, 2), "segments": s}
        print(f"{f.stem}  {len(x) / sr:.2f} s")
        for a, b in s:
            print(f"   {a:6.2f} -> {b:6.2f}")
    (ICI / "phrases.json").write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
