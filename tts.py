"""O'zbekcha ovoz (Microsoft Edge neural TTS) + so'z vaqtlari."""
import asyncio
import json
import subprocess
from pathlib import Path

import edge_tts

VOICES = {
    "madina": "uz-UZ-MadinaNeural",
    "sardor": "uz-UZ-SardorNeural",
}


async def _synth(text: str, voice: str, out_mp3: Path, rate: str, pitch: str):
    comm = edge_tts.Communicate(text, VOICES.get(voice, voice), rate=rate, pitch=pitch, boundary="WordBoundary")
    words = []
    with open(out_mp3, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                # offset/duration are in 100ns ticks
                t0 = chunk["offset"] / 1e7
                words.append({"t0": t0, "t1": t0 + chunk["duration"] / 1e7, "text": chunk["text"]})
    return words


def duration_of(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)


def _sanitize(text: str) -> str:
    import re
    t = re.sub(r"[^\w\s'’ʼ.,!?;:\-—–()%+/]", " ", text)
    return re.sub(r"\s+", " ", t).strip()


def _try_synth(text: str, voice: str, out_mp3: Path, rate: str, pitch: str, attempts: int = 3):
    import time
    last = None
    for k in range(attempts):
        try:
            words = asyncio.run(_synth(text, voice, out_mp3, rate, pitch))
            if out_mp3.exists() and out_mp3.stat().st_size > 1000:
                return words
            last = RuntimeError("bo'sh audio")
        except Exception as e:  # NoAudioReceived, tarmoq, WebSocket
            last = e
        time.sleep(1.5 * (k + 1))
    raise last


def synthesize(text: str, voice: str, out_mp3: Path, rate: str = "+0%", pitch: str = "+0Hz") -> dict:
    """Matnni ovozga aylantiradi. Qaytaradi: {"path", "duration", "words"}.
    Xato bo'lsa: qayta urinish -> tozalangan matn -> gaplarga bo'lib yig'ish."""
    import re
    out_mp3.parent.mkdir(parents=True, exist_ok=True)
    text = text.strip() or "…"
    try:
        words = _try_synth(text, voice, out_mp3, rate, pitch)
    except Exception:
        clean = _sanitize(text)
        try:
            words = _try_synth(clean, voice, out_mp3, rate, pitch)
        except Exception:
            # oxirgi chora: gapma-gap sintez qilib, birlashtiramiz
            parts = [x for x in re.split(r"(?<=[.!?…])\s+", clean) if x.strip()] or [clean]
            words, files, offset = [], [], 0.0
            for j, part in enumerate(parts):
                pf = out_mp3.with_name(out_mp3.stem + f"_p{j}.mp3")
                try:
                    w = _try_synth(part, voice, pf, rate, pitch, attempts=2)
                except Exception:
                    print(f"  ! TTS bu bo'lakni o'qiy olmadi, tashlab ketildi: {part[:60]}")
                    continue
                d = duration_of(pf)
                words += [{"t0": offset + x["t0"], "t1": offset + x["t1"], "text": x["text"]} for x in w]
                files.append(pf); offset += d + 0.15
            if not files:
                raise RuntimeError(f"TTS umuman ovoz bera olmadi: {text[:80]}")
            lst = out_mp3.with_suffix(".txt")
            lst.write_text("".join(f"file '{f.resolve()}'\n" for f in files))
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
                            "-af", "apad=pad_dur=0.15", "-c:a", "libmp3lame", "-q:a", "2", str(out_mp3)], check=True)
    dur = duration_of(out_mp3)
    # edge-tts ba'zan so'zlarni bo'lak-bo'lak beradi; oxirgi so'z tugashini audio uzunligiga tortamiz
    if words:
        words[-1]["t1"] = min(max(words[-1]["t1"], words[-1]["t0"] + 0.15), dur)
    meta = {"path": str(out_mp3), "duration": dur, "words": words}
    out_mp3.with_suffix(".json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    return meta


if __name__ == "__main__":
    import sys
    m = synthesize(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "madina", Path("out/_tts_test.mp3"))
    print(json.dumps(m, ensure_ascii=False, indent=1))
