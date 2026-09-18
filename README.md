# videogen — prompt → Uzbek-voiced Instagram Reels

> **EN:** Turn a one-line prompt (or a full storyboard) into a finished 9:16 video: Claude writes the script, Microsoft neural TTS narrates it in Uzbek (with correct pronunciation of English terms), a Chromium-rendered motion-graphics engine draws every frame deterministically, and ffmpeg mixes voice, music (with ducking) and sound effects. No AI-video API needed.
>
> **UZ:** Bitta jumla (yoki to'liq storyboard) → tayyor Reels video: skriptni Claude yozadi, o'zbekcha ovoz (Madina/Sardor), animatsiyali sahnalar, personajlar, musiqa + effektlar, brend end-card.

```
Prompt ─► Claude (planner.py: full JSON plan) ─► Edge-TTS (Uzbek voice + word timings)
       ─► Chromium (renderer/*.html: every frame = f(t)) ─► ffmpeg (voice + ducked music + SFX) ─► out/<name>.mp4
```

## Quick start / Tez boshlash
```bash
git clone https://github.com/Abdivasiyev2008/Videogen-Uz.git && cd Videogen-Uz
./setup.sh                    # venv + deps + Chromium (needs ffmpeg: brew install ffmpeg)
# Claude: either `claude` (Claude Code, logged in) — or ANTHROPIC_API_KEY in .env
./.venv/bin/python make.py "Ommaviy Wi-Fi qanchalik xavfli? 30 soniya, jiddiy erkak ovozi"
```
Output: `out/<name>.mp4` (9:16 1080×1920 by default; `--format youtube` → 16:9 1920×1080, 30 fps), `out/<name>.json` (the plan — edit & re-render), `out/<name>.caption.txt` (Instagram caption + music credit).

```bash
make.py "..." --plan-only                  # only show the plan
make.py --prompt-file storyboard.txt       # long storyboard from a file
make.py --script out/<name>.json           # re-render an edited plan (no Claude call)
make.py "..." --format youtube            # 16:9 long-form (60–180 s); reels|shorts|9:16 = vertical
make.py "..." --voice sardor --template cyber --backend cli|api
```

## What Claude decides / Claude nima hal qiladi
Template (`template` universal / `cyber` dark-neon), scene types & fields, narration (short TTS-friendly Uzbek), voice (Madina/Sardor + rate/pitch), SFX plan (whoosh/hit/blip/swell/glitch), music mood & volume curve, animated characters, pronunciation entries for foreign words, the brand end-card, and the Instagram caption. The two files in `examples/` are shown to Claude as quality references.

## Your brand / O'z kanalingiz
Edit **`brand.json`** (name, handle, tagline, CTA, narration, accent color) and drop your logo at **`assets/logo.png`**. Without a logo the end-card renders a text wordmark in the same style.

## Pronunciation / Talaffuz
Uzbek TTS reads English letter-by-letter, so `assets/pronounce.json` (~220 terms) maps terms to phonetic Uzbek (`username → yuzerneym`, `cyber security → sayber sekyuriti`). Only the audio changes — on-screen text stays original. Claude adds missing words per script (`pronunciations`), and `make.py` prints a warning listing any word that still looks foreign after substitution. Add your own entries freely.

## Scene types / Sahna turlari
- **template**: `hook`, `text`, `list`, `stat` (count-up), `quote`, `compare`, `outro` — themes `midnight ocean forest sunset candy gold`, karaoke captions, `person`: `walk run typing phone idle wave point`.
- **cyber**: `cyber_hook` (terminal + hooded hacker), `cyber_username`, `cyber_email`, `cyber_phone`, `cyber_connect` (data graph), `cyber_shield`, `cyber_outro` (glitch) + all generic types in dark style.
- **brand**: always last.

## Project layout
| File | Role |
|---|---|
| `make.py` | CLI |
| `planner.py` | Claude "director": system prompt, JSON schema, CLI/API backends, `finalize()` sanity fixes |
| `tts.py` | edge-tts (uz-UZ Madina/Sardor), word boundaries, retries & fallbacks |
| `pronounce.py` + `assets/pronounce.json` | phonetic substitution for TTS |
| `render.py` | timeline, frame capture via Playwright, audio mix (sidechain ducking, loudnorm −14 LUFS) |
| `sfx.py` | procedural sound effects (numpy) |
| `renderer/template.html`, `renderer/cyber.html` | scene templates — every frame is a pure function `seek(t)` |
| `renderer/people.js` | procedural SVG character rig (FK, 8 animations) |
| `assets/music/` | Kevin MacLeod tracks, CC BY 4.0 — see `CREDITS.md`, **attribution required in your post** |

## Tuning
Timing: `render.py` (`LEAD`, `TAIL`, `MIN_SCENE`) or per-script `lead/tail/min/extra`. Design: CSS in the templates. Script rules: `planner.SYSTEM`. Add a pose: `people.js → P`.

## Requirements
Python 3.9+, ffmpeg, Chromium (installed by Playwright), internet for TTS. macOS fonts (Avenir Next / SF Mono) are used when present; falls back to system fonts.

## License
MIT (code). Music: CC BY 4.0, Kevin MacLeod — not covered by MIT.
