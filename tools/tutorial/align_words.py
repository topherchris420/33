"""Listen to the narration: transcribe each line and record word timings.

Optional quality check. Uses faster-whisper (MIT) locally; nothing leaves the
machine. Prints what the voice actually said next to the caption text, and
writes build/tutorial/narration/words.json so timeline.py can land visual
beats on specific words.

    python tools/tutorial/align_words.py
"""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parents[2]
NARR = ROOT / "build" / "tutorial" / "narration"


def main():
    from faster_whisper import WhisperModel

    model = WhisperModel("base.en", device="cpu", compute_type="int8")
    script = {l["id"]: l["text"] for l in json.loads((ROOT / "tools" / "tutorial" / "narration.json").read_text(encoding="utf-8"))["lines"]}
    words = {}
    for lid in script:
        audio, sr = sf.read(NARR / f"{lid}.wav", dtype="float32")
        audio16 = resample_poly(audio, 1, sr // 16000).astype(np.float32)
        segments, _ = model.transcribe(audio16, beam_size=5, word_timestamps=True, language="en")
        heard, timing = [], []
        for seg in segments:
            heard.append(seg.text.strip())
            for w in seg.words:
                timing.append({"w": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3)})
        words[lid] = timing
        print(f"{lid:5s} heard: {' '.join(heard)}\n      text:  {script[lid]}")
    (NARR / "words.json").write_text(json.dumps(words, indent=1) + "\n")


if __name__ == "__main__":
    main()
