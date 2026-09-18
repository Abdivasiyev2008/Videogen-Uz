"""Skript JSON -> tayyor video (kadrlar Chromium'da, montaj ffmpeg'da)."""
from __future__ import annotations
import json
import random
import re
import subprocess
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

import planner
import pronounce
import sfx
import tts

ROOT = Path(__file__).parent
TEMPLATES = ROOT / "renderer"
MUSIC_DIR = ROOT / "assets" / "music"

FPS = 30
FORMATS = {"vertical": (1080, 1920), "wide": (1920, 1080)}
LEAD = 0.45      # sahna boshlanib, ovoz boshlangunicha
TAIL = 0.7       # ovoz tugagach, keyingi sahnagacha
MIN_SCENE = {"hook": 3.0, "outro": 3.5, "list": 4.0, "compare": 4.5, "brand": 3.5}

MOOD_TRACKS = {
    "energetic": ["Voltaic.mp3", "Cyborg Ninja.mp3", "Electro Cabello.mp3"],
    "calm": ["Deliberate Thought.mp3", "Digital Lemonade.mp3"],
    "inspiring": ["Pamgaea.mp3", "Electrodoodle.mp3", "Rhinoceros.mp3"],
}


def log(msg):
    print(f"  ▸ {msg}", flush=True)


def _logo_uri(script: dict) -> str | None:
    cand = [Path(script["logo"])] if script.get("logo") else []
    cand += [ROOT / planner.BRAND.get("logo", "assets/logo.png")]
    cand += [ROOT / "assets" / n for n in ("logo.png", "logo.jpg", "logo.jpeg", "logo.webp", "logo.svg")]
    for c in cand:
        if c.exists():
            return c.resolve().as_uri()
    return None


def build_timeline(script: dict, voice: str, work: Path) -> dict:
    """Har sahna uchun ovoz yasab, boshlanish/tugash vaqtlarini hisoblaydi."""
    t = 0.0
    scenes = []
    for i, sc in enumerate(script["scenes"]):
        log(f"ovoz {i+1}/{len(script['scenes'])}: {sc['narration'][:50]}…")
        extra = dict(script.get("pronunciations") or {})
        if planner.BRAND.get("say"):
            extra.setdefault(planner.BRAND["name"], planner.BRAND["say"])
        spoken = pronounce.for_tts(sc["narration"], extra)  # inglizcha so'zlar talaffuzi
        meta = tts.synthesize(spoken, voice, work / f"voice_{i:02d}.mp3",
                              rate=script.get("voice_rate", "+0%"), pitch=script.get("voice_pitch", "+0Hz"))
        # subtitrlarda asl yozuv ko'rinsin (so'zlar soni mos kelsa)
        orig = [w for w in re.split(r"\s+", sc["narration"].strip()) if w]
        orig = [re.sub(r"^[^\w']+|[^\w']+$", "", w) for w in orig]
        if len(orig) == len(meta["words"]):
            for w, o in zip(meta["words"], orig):
                w["text"] = o or w["text"]
        lead, tail = script.get("lead", LEAD), script.get("tail", TAIL)
        dur = max(lead + meta["duration"] + tail + sc.get("extra", 0), sc.get("min", MIN_SCENE.get(sc["type"], 2.5)))
        s = dict(sc)
        s["start"] = round(t, 3)
        s["end"] = round(t + dur, 3)
        s["voice_at"] = round(t + lead, 3)
        s["voice_path"] = meta["path"]
        s["words"] = [{"t0": t + lead + w["t0"], "t1": t + lead + w["t1"], "text": w["text"]} for w in meta["words"]]
        scenes.append(s)
        t += dur
    return {
        "brand": script.get("brand", ""),
        "theme": script.get("theme", "midnight"),
        "captions": script.get("captions", True),
        "logo": _logo_uri(script),
        "brand_info": planner.BRAND,
        "duration": round(t, 3),
        "scenes": scenes,
    }


def render_frames(plan: dict, work: Path, template: str = "template") -> Path:
    W, H = FORMATS.get(plan.get("format", "vertical"), FORMATS["vertical"])
    """Chromium'da har kadrni chizib, ffmpeg'ga uzatadi -> ovozsiz mp4."""
    silent = work / "video_silent.mp4"
    n_frames = int(plan["duration"] * FPS) + 1
    ff = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-vcodec", "mjpeg", "-r", str(FPS), "-i", "-",
         "-c:v", "libx264", "-preset", "fast", "-crf", "17", "-pix_fmt", "yuv420p", str(silent)],
        stdin=subprocess.PIPE,
    )
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        page.goto((TEMPLATES / f"{template}.html").as_uri())
        page.evaluate("plan => window.setup(plan)", plan)
        page.wait_for_timeout(300)  # shriftlar/emoji yuklansin
        for i in range(n_frames):
            page.evaluate("t => window.seek(t)", i / FPS)
            ff.stdin.write(page.screenshot(type="jpeg", quality=92))
            if i % (FPS * 5) == 0:
                log(f"kadr {i}/{n_frames}  ({i/FPS:.0f}s)")
        browser.close()
    ff.stdin.close()
    ff.wait()
    if ff.returncode != 0:
        raise RuntimeError("ffmpeg kadrlarni yozishda xato")
    return silent


def pick_music(mood: str) -> Path | None:
    names = MOOD_TRACKS.get(mood, []) or sum(MOOD_TRACKS.values(), [])
    cands = [MUSIC_DIR / n for n in names if (MUSIC_DIR / n).exists()]
    if not cands:
        cands = list(MUSIC_DIR.glob("*.mp3"))
    return random.choice(cands) if cands else None


def resolve_sfx(script: dict, plan: dict, work: Path) -> list[tuple[Path, float]]:
    """script["sfx"]: [{"name":"whoosh","at":0.0} | {"name":"glitch","scene":6,"offset":-0.6,"from":"end"}]"""
    out = []
    for e in script.get("sfx", []):
        if "scene" in e:
            sc = plan["scenes"][e["scene"]]
            base = sc["end"] if e.get("from") == "end" else sc["start"]
            at = base + e.get("offset", 0)
        else:
            at = e.get("at", 0)
        at = max(0.0, min(at, plan["duration"] - 0.05))
        out.append((sfx.make(e["name"], work), at, e.get("gain", 1.0)))
    return out


def music_volume_expr(script: dict, plan: dict, base: float) -> str:
    """script["music_curve"]: [{"scene":4,"gain":1.3},{"scene":5,"gain":0.6}] -> ffmpeg volume ifodasi"""
    expr = "1"
    for seg in reversed(script.get("music_curve", [])):
        sc = plan["scenes"][seg["scene"]]
        expr = f"if(between(t,{sc['start']},{sc['end']}),{seg['gain']},{expr})"
    return f"{base}*({expr})"


def mix_and_mux(plan: dict, silent: Path, music: Path | None, out: Path, script: dict | None = None, work: Path | None = None):
    """Ovozlarni o'z vaqtiga qo'yib, musiqani ovoz ostida pasaytirib (ducking) birlashtiradi."""
    script = script or {}
    total = plan["duration"]
    inputs = ["-i", str(silent)]
    fc = []
    voices = []
    sfx_list = resolve_sfx(script, plan, work or out.parent) if script.get("sfx") else []
    for i, sc in enumerate(plan["scenes"]):
        inputs += ["-i", sc["voice_path"]]
        ms = int(sc["voice_at"] * 1000)
        fc.append(f"[{i+1}:a]aresample=48000,aformat=channel_layouts=stereo,adelay={ms}|{ms}[v{i}]")
        voices.append(f"[v{i}]")
    n = len(voices)
    fc.append(f"{''.join(voices)}amix=inputs={n}:normalize=0:dropout_transition=0,apad=whole_dur={total},atrim=duration={total},volume=1.6,asplit=2[voice][vsc]")
    buses = ["[voice]"]
    idx = n + 1
    if music:
        inputs += ["-stream_loop", "-1", "-i", str(music)]
        vol = music_volume_expr(script, plan, script.get("music_volume", 0.35))
        fc.append(
            f"[{idx}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=duration={total},"
            f"afade=t=in:d=0.8,afade=t=out:st={max(total-2.5,0)}:d=2.5,volume='{vol}':eval=frame[mus]"
        )
        fc.append("[mus][vsc]sidechaincompress=threshold=0.02:ratio=10:attack=40:release=500:makeup=1[ducked]")
        buses.append("[ducked]"); idx += 1
    else:
        fc.append("[vsc]anullsink")
    if sfx_list:
        fx = []
        for k, (path, at, gain) in enumerate(sfx_list):
            inputs += ["-i", str(path)]
            ms = int(at * 1000)
            fc.append(f"[{idx}:a]volume={gain},adelay={ms}|{ms}[fx{k}]"); fx.append(f"[fx{k}]"); idx += 1
        fc.append(f"{''.join(fx)}amix=inputs={len(fx)}:normalize=0:dropout_transition=0,apad=whole_dur={total},atrim=duration={total},volume=0.9[sfx]")
        buses.append("[sfx]")
    fc.append(f"{''.join(buses)}amix=inputs={len(buses)}:normalize=0,alimiter=limit=0.9:level=false,loudnorm=I=-14:TP=-2.5:LRA=11[a]")
    cmd = ["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(fc),
           "-map", "0:v", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
           "-movflags", "+faststart", "-shortest", str(out)]
    subprocess.run(cmd, check=True)


def make_video(script: dict, out: Path, voice: str = "madina", work: Path | None = None, fmt: str | None = None) -> Path:
    work = work or (ROOT / "out" / "_work" / out.stem)
    work.mkdir(parents=True, exist_ok=True)
    fmt = fmt or script.get("format", "vertical")
    log("1/4 ovoz yaratilmoqda")
    plan = build_timeline(script, voice, work)
    plan["format"] = fmt
    log(f"format: {fmt} ({'x'.join(map(str, FORMATS[fmt]))})")
    (work / "plan.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1))
    log(f"umumiy uzunlik: {plan['duration']:.1f}s, {len(plan['scenes'])} sahna")
    log("2/4 kadrlar render qilinmoqda")
    silent = render_frames(plan, work, script.get("template", "template"))
    music = (MUSIC_DIR / script["music_file"]) if script.get("music_file") else pick_music(script.get("music_mood", "inspiring"))
    log(f"3/4 musiqa: {music.name if music else 'yo‘q'}")
    log("4/4 audio aralashtirilmoqda")
    mix_and_mux(plan, silent, music, out, script, work)
    script["_music"] = music.name if music else None
    return out


if __name__ == "__main__":
    script = json.loads(Path(sys.argv[1]).read_text())
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "out" / "video.mp4"
    make_video(script, out, sys.argv[3] if len(sys.argv) > 3 else "madina")
    print(out)
