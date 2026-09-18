#!/usr/bin/env python3
"""
Prompt -> o'zbekcha ovozli Instagram Reels video.

  python make.py "Uyqu haqida 3 ta hayratlanarli fakt"          # Claude skript yozadi (API kalit kerak)
  python make.py --script examples/ai_faktlar.json              # tayyor skriptdan
  python make.py "..." --voice sardor --out out/uyqu.mp4 --save-script
"""
import argparse
import json
import re
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

import planner  # noqa: E402
import render   # noqa: E402


def slug(s: str) -> str:
    s = re.sub(r"[^\w\s-]", "", s.lower()).strip()
    return re.sub(r"[\s_-]+", "-", s)[:40] or "video"


def main():
    ap = argparse.ArgumentParser(description="Prompt -> Reels video (o'zbekcha ovoz bilan)")
    ap.add_argument("prompt", nargs="?", help="Video mavzusi (o'zbekcha)")
    ap.add_argument("--script", help="Tayyor skript JSON fayli (Claude'siz)")
    ap.add_argument("--voice", default=None, choices=["madina", "sardor"], help="Berilmasa skriptdagi voice ishlatiladi")
    ap.add_argument("--template", default="auto", choices=["auto", "template", "cyber"], help="Claude uchun shablon ko'rsatmasi")
    ap.add_argument("--out", help="Chiqish fayli (.mp4)")
    ap.add_argument("--format", default=None, choices=["vertical", "wide", "9:16", "16:9", "reels", "youtube", "shorts"],
                    help="vertical/9:16/reels/shorts = 1080x1920, wide/16:9/youtube = 1920x1080 (berilmasa skriptdagi format)")
    ap.add_argument("--backend", default="auto", choices=["auto", "api", "cli"], help="Claude: api (kalit) yoki cli (Claude Code obunasi)")
    ap.add_argument("--prompt-file", help="Promptni fayldan o'qish (uzun storyboard uchun)")
    ap.add_argument("--save-script", action="store_true", help="Claude yozgan skriptni JSON qilib saqlash")
    ap.add_argument("--plan-only", action="store_true", help="Faqat skript yozib chiqish, video yasamaslik")
    a = ap.parse_args()

    if a.prompt_file:
        a.prompt = Path(a.prompt_file).read_text()
    fmt = {"9:16": "vertical", "reels": "vertical", "shorts": "vertical", "16:9": "wide", "youtube": "wide"}.get(a.format, a.format)
    if a.script:
        script = json.loads(Path(a.script).read_text())
        name = Path(a.script).stem
    elif a.prompt:
        b = planner.backend(a.backend)
        if not b:
            sys.exit("✗ Claude topilmadi: .env ga ANTHROPIC_API_KEY qo'ying yoki Claude Code'ga login qiling (`claude`).")
        print(f"▸ Claude skript yozmoqda… ({'API kalit' if b=='api' else 'Claude Code obunasi'})", flush=True)
        script = planner.plan(a.prompt, a.voice, a.template, a.backend, fmt)
        name = slug(script.get("title") or a.prompt)
        # Claude yozgan skript doim saqlanadi — xato bo'lsa --script bilan qayta yasash mumkin
        p = ROOT / "out" / f"{name}.json"
        p.parent.mkdir(exist_ok=True)
        p.write_text(json.dumps(script, ensure_ascii=False, indent=1))
        print(f"▸ skript saqlandi: {p}")
        if a.plan_only:
            print(json.dumps(script, ensure_ascii=False, indent=1))
            return
    else:
        ap.error("prompt yoki --script bering")

    out = Path(a.out) if a.out else ROOT / "out" / f"{name}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    voice = a.voice or script.get("voice", "madina")
    fmt = fmt or script.get("format", "vertical")
    print(f"▸ {script.get('title','')}  |  shablon: {script.get('template','template')}  |  format: {fmt}  |  ovoz: {voice}  |  {len(script['scenes'])} sahna")
    # talaffuz auditi: lug'atdan keyin ham xorijiy ko'rinadigan so'zlar
    import pronounce
    sus = sorted({w for sc in script["scenes"] for w in pronounce.audit(sc["narration"], script.get("pronunciations"))}, key=str.lower)
    if sus:
        print(f"⚠ Talaffuzi shubhali so'zlar (assets/pronounce.json yoki skriptdagi pronunciations ga qo'shing): {', '.join(sus)}")
    render.make_video(script, out, voice, fmt=fmt)
    cap_lines = [script["caption_text"]] if script.get("caption_text") else []
    if script.get("_music"):  # CC BY musiqa uchun attribution (majburiy)
        cap_lines.append(f'Music: "{Path(script["_music"]).stem}" by Kevin MacLeod (incompetech.com). Licensed under Creative Commons: By Attribution 4.0')
    if cap_lines:
        cap = out.with_suffix(".caption.txt"); cap.write_text("\n\n".join(cap_lines)); print(f"▸ Instagram tavsifi: {cap}")
    print(f"\n✓ Tayyor: {out}")


if __name__ == "__main__":
    main()
