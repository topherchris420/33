"""Synthesize the tutorial narration, one WAV per line, with a local neural voice.

Uses Kokoro-82M (Apache-2.0) through kokoro-onnx. Nothing is sent over the
network and no API key is involved. Model files are not committed; download
them once (see docs/TUTORIAL_FILM.md) and point KOKORO_MODEL_DIR at them.

    python tools/tutorial/build_narration.py [--only s5h,s5i]

Writes build/tutorial/narration/<id>.wav (48 kHz mono, silence trimmed) and
build/tutorial/narration/durations.json.
"""
import argparse
import json
import os
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "tools" / "tutorial" / "narration.json"
OUT = ROOT / "build" / "tutorial" / "narration"
SR = 48000


def trim(audio, sr, floor_db=-48.0, pad=0.03):
    level = 10 ** (floor_db / 20)
    env = np.convolve(np.abs(audio), np.ones(256) / 256, mode="same")
    idx = np.where(env > level)[0]
    if len(idx) == 0:
        return audio
    a = max(0, idx[0] - int(pad * sr))
    b = min(len(audio), idx[-1] + int(pad * sr))
    return audio[a:b]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", default="")
    args = parser.parse_args()
    from kokoro_onnx import Kokoro

    model_dir = Path(os.environ.get("KOKORO_MODEL_DIR", ROOT / "build" / "tts"))
    kokoro = Kokoro(str(model_dir / "kokoro-v1.0.onnx"), str(model_dir / "voices-v1.0.bin"))
    script = json.loads(SCRIPT.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    durations_path = OUT / "durations.json"
    durations = json.loads(durations_path.read_text()) if durations_path.exists() else {}
    only = {x for x in args.only.split(",") if x}
    for line in script["lines"]:
        if only and line["id"] not in only:
            continue
        text = line.get("say", line["text"])
        samples, sr = kokoro.create(
            text, voice=line.get("voice", script["voice"]),
            speed=line.get("speed", script["speed"]), lang="en-us",
        )
        audio = resample_poly(np.asarray(samples, dtype=np.float64), SR, sr)
        audio = trim(audio, SR)
        peak = np.max(np.abs(audio)) or 1.0
        audio = audio / peak * 0.89
        sf.write(OUT / f"{line['id']}.wav", audio.astype(np.float32), SR, subtype="FLOAT")
        durations[line["id"]] = round(len(audio) / SR, 3)
        print(f"{line['id']:5s} {durations[line['id']]:6.2f}s  {line['text']}")
    durations_path.write_text(json.dumps(durations, indent=2) + "\n")
    print(f"total speech {sum(durations.values()):.1f}s")


if __name__ == "__main__":
    main()
