"""Prompt -> to'liq video skripti (JSON). Claude API orqali.

Claude bu yerda "rejissyor": shablonni tanlaydi, sahnalarni, diktor matnini, SFX'larni,
musiqa dinamikasini, personajlarni va brend end-card'ni rejalashtiradi.
"""
from __future__ import annotations
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import anthropic

MODEL = "claude-opus-5"
ROOT = Path(__file__).parent


def load_brand() -> dict:
    """brand.json — kanal nomi, handle, CTA (o'z kanalingizga moslang)."""
    d = {"name": "MY CHANNEL", "handle": "@mychannel", "tagline": "", "cta": "Obuna bo'ling",
         "narration": "Kanalga obuna bo'ling.", "say": "", "accent": "#f26a1b", "bg": "#070b16", "logo": "assets/logo.png"}
    p = ROOT / "brand.json"
    if p.exists():
        d.update(json.loads(p.read_text()))
    return d


BRAND = load_brand()

GENERIC_TYPES = ["hook", "text", "list", "stat", "quote", "compare", "outro"]
CYBER_TYPES = ["cyber_hook", "cyber_username", "cyber_email", "cyber_phone", "cyber_connect", "cyber_shield", "cyber_outro"]
SCENE_TYPES = GENERIC_TYPES + CYBER_TYPES + ["brand"]
PERSONS = ["none", "walk", "run", "typing", "phone", "idle", "wave", "point"]
THEMES = ["midnight", "sunset", "forest", "ocean", "candy", "gold"]
MOODS = ["calm", "energetic", "inspiring", "dark"]
SFX_NAMES = ["whoosh", "hit", "glitch", "blip", "swell"]
MUSIC = {
    "dark": ["Cyborg Ninja.mp3", "Voltaic.mp3"],
    "energetic": ["Voltaic.mp3", "Electro Cabello.mp3", "Cyborg Ninja.mp3"],
    "calm": ["Deliberate Thought.mp3", "Digital Lemonade.mp3"],
    "inspiring": ["Pamgaea.mp3", "Electrodoodle.mp3", "Rhinoceros.mp3"],
}


# ---------------------------------------------------------------- JSON schema
def _s(): return {"anyOf": [{"type": "string"}, {"type": "null"}]}
def _n(): return {"anyOf": [{"type": "number"}, {"type": "null"}]}
def _arr(item): return {"anyOf": [{"type": "array", "items": item}, {"type": "null"}]}
def _obj(props, req=None):
    return {"type": "object", "properties": props, "required": req if req is not None else list(props), "additionalProperties": False}
def _optobj(props): return {"anyOf": [_obj(props), {"type": "null"}]}

COL = {"title": {"type": "string"}, "items": {"type": "array", "items": {"type": "string"}}}
CARD = _obj({"icon": {"type": "string", "enum": ["map", "post", "photo"]}, "label": {"type": "string"}})

SCENE = _obj({
    "type": {"type": "string", "enum": SCENE_TYPES},
    "narration": {"type": "string"},
    "min": _n(), "extra": _n(), "cut": {"anyOf": [{"type": "string", "enum": ["hard"]}, {"type": "null"}]},
    "person": {"anyOf": [{"type": "string", "enum": PERSONS}, {"type": "null"}]},
    # generic
    "emoji": _s(), "title": _s(), "subtitle": _s(), "body": _s(),
    "items": _arr({"type": "string"}), "value": _s(), "label": _s(),
    "quote": _s(), "author": _s(), "left": _optobj(COL), "right": _optobj(COL), "cta": _s(),
    # cyber
    "lines": _arr({"type": "string"}), "step": _s(), "sub": _s(), "username": _s(), "found": _arr({"type": "string"}),
    "email": _s(), "chips": _arr({"type": "string"}), "phone": _s(), "cards": _arr(CARD),
    "nodes": _arr({"type": "string"}), "q": _s(), "answer": _s(), "answer_at": _n(),
    "l1": _s(), "l2": _s(), "l3": _s(),
})

SFX = _obj({"name": {"type": "string", "enum": SFX_NAMES}, "scene": {"type": "integer"}, "offset": {"type": "number"},
            "from": {"anyOf": [{"type": "string", "enum": ["start", "end"]}, {"type": "null"}]}, "gain": {"type": "number"}})
CURVE = _obj({"scene": {"type": "integer"}, "gain": {"type": "number"}})

SCHEMA = _obj({
    "title": {"type": "string"},
    "brand": {"type": "string"},
    "template": {"type": "string", "enum": ["template", "cyber"]},
    "theme": {"type": "string", "enum": THEMES},
    "voice": {"type": "string", "enum": ["madina", "sardor"]},
    "voice_rate": {"type": "string"},
    "voice_pitch": {"type": "string"},
    "music_mood": {"type": "string", "enum": MOODS},
    "music_volume": {"type": "number"},
    "music_curve": {"type": "array", "items": CURVE},
    "sfx": {"type": "array", "items": SFX},
    "captions": {"type": "boolean"},
    "lead": {"type": "number"}, "tail": {"type": "number"},
    "pronunciations": {"type": "array", "items": _obj({"word": {"type": "string"}, "say": {"type": "string"}})},
    "caption_text": {"type": "string"},
    "scenes": {"type": "array", "items": SCENE},
})


# ---------------------------------------------------------------- system prompt
def _example(name: str) -> str:
    p = ROOT / "examples" / name
    return p.read_text() if p.exists() else "{}"


SYSTEM = f"""Sen {BRAND["name"]} kanali uchun Instagram Reels videolarining REJISSYORI va SSENARISTISAN.
Foydalanuvchi mavzu yoki batafsil storyboard beradi. Sen video-render dvigateli uchun TO'LIQ JSON reja qaytarasan.
Natija sifati "premium" bo'lishi shart: kuchli hook, ritm, vizual xilma-xillik, o'ylangan ovoz effektlari, brend bilan tugash.

════════ 1. TIL VA DIKTOR (narration) ════════
- O'zbek tili, LOTIN alifbosi, apostrof uchun oddiy ' (o', g'). Og'zaki, samimiy, aniq. Ovoz sintezatori o'qiydi:
  qisqa gaplar (5–14 so'z), murakkab qo'shma gaplar yo'q, raqamlarni so'z bilan yoz ("yetmish yetti foiz").
- Har sahnada narration ekrandagi matnni TAKRORLAMAYDI — to'ldiradi, tushuntiradi, hissiyot beradi.
- Foydalanuvchi "Voice-over" matnini bergan bo'lsa — uni AYNAN ishlat (faqat imlo/punktuatsiya tuzatish mumkin).
- Inglizcha terminlar (username, email, hacker, cyber security, AI, VPN...) matnda qolsin — dvigatel talaffuz lug'ati bilan
  o'zbekcha o'qiydi. Lug'atda bo'lmasligi mumkin bo'lgan HAR BIR inglizcha/xorijiy so'z uchun "pronunciations" ro'yxatiga
  fonetik yozuv qo'sh (masalan {{"word":"deepfake","say":"dipfeyk"}}, {{"word":"Netflix","say":"netfliks"}}).
- Ovoz: jiddiy/texnik/qo'rqinchli mavzu → "sardor" (rate "+6%", pitch "-3Hz"); do'stona/lifestyle/ta'lim → "madina" (rate "+4%").
  Foydalanuvchi ovozni aytsa — unga bo'ysun.

════════ 2. UZUNLIK VA RITM ════════
- Sahna davomiyligi ≈ narration_so'zlar/2.9 + 0.7 soniya. Foydalanuvchi so'ragan umumiy uzunlikka moslash (odatda 30–50 s).
  Matn juda uzun bo'lsa — qisqartir, lekin foydalanuvchi bergan aniq Voice-over matnini o'zgartirma.
- 6–9 sahna. Ketma-ket ikkita bir xil tur bo'lmasin. Birinchi sahna doim hook (hook yoki cyber_hook), OXIRGI sahna DOIM "brand".
- lead/tail: energik video → lead 0.3, tail 0.35; sokin → lead 0.45, tail 0.7.

════════ 3. SHABLONLAR ════════
"template" (universal, rangli): mavzu — ta'lim, faktlar, motivatsiya, lifestyle, biznes, AI umumiy.
  Sahna turlari va maydonlari:
  hook: emoji(1 ta), title(2–5 so'z), subtitle?      text: emoji?, title, body(1 gap)
  list: title, items[3–4] (har biri 2–5 so'z)         stat: value("77%","3 mln"), label
  quote: quote, author                                 compare: title, left{{title,items[2-3]}}, right{{...}}
  outro: emoji, title, subtitle?, cta
  person: hook/outro→"wave", tushuntirish→"point", texnologiya→"typing", telefon/ijtimoiy→"phone", harakat→"walk"/"run"; list/compare→"none".
  theme: texnologiya→midnight/ocean, tabiat/salomatlik→forest, motivatsiya→sunset/gold, ko'ngilochar→candy.
  captions: true (karaoke subtitr).

"cyber" (qorong'i kinematik, neon ko'k, terminal, hacker): mavzu — kiberxavfsizlik, hacking, OSINT, maxfiylik, IT xavf.
  Sahna turlari (vizual tavsif → maydonlar):
  cyber_hook   — terminal oynalari, kapyushonli hacker orqadan yozib o'tiribdi, sarlavha qatorma-qator → lines[2–3] (KATTA HARF, 1–3 so'z), min≈3.4
  cyber_username — profil interfeysi, username harfma-harf yoziladi, platformalar "TOPILDI" → step("1. Username"), username(soxta, masalan cyber_user01), found[3–4], sub(1 gap)
  cyber_email  — konvert → email oynasi (maskalanadi) → servis chiplari → step, email(soxta example.com), chips[3–4] ("!" prefiksi = qizil/xavfli), sub?
  cyber_phone  — telefon, maskalangan raqam, radar, kartalar; odam telefon ko'rib turadi → step, phone("+998 ** *** ** **"), cards[3] {{icon: map|post|photo, label}}
  cyber_connect — tarmoq: node'lar markazdagi inson profiliga ulanadi → nodes[4–6] (KATTA HARF inglizcha/qisqa), q(savol), answer(javob), answer_at(sekund, ≈2.4), min≈5
  cyber_shield — hard cut + flash, qalqon, galochka, zarrachalar, odam ko'rsatadi → l1(asosiy tezis KATTA HARF), l2(ikkinchi qator), cut:"hard"
  cyber_outro  — neon chiziqlar, glitch → l1("1-QISM"), l2("CYBER SECURITY"), l3("Davomi bor..."), min≈3.2, extra≈0.6
  Cyber'da captions: false (ekrandagi matn subtitr vazifasini bajaradi). Boshqa mavzuga cyber_* turlarni ishlatma.
  Cyber'da generic turlarni ham qo'shish mumkin (masalan stat, list) — ular qorong'i uslubda chiziladi.

"brand" (har ikkala shablonda, DOIM oxirgi sahna): {BRAND["name"]} logosi, CTA → narration("{BRAND["narration"]}" yoki mavzuga mos 1 gap),
  cta("{BRAND["cta"]}" / "Saqlab qo'ying" / "Davomini kuting"), sub("{BRAND["handle"]}"), min 3.8, cyber'da cut:"hard".

════════ 4. OVOZ EFFEKTLARI (sfx) va MUSIQA ════════
sfx elementlari: {{name, scene(indeks, 0 dan), offset(sekund), from("start"|"end"), gain(0.3–1.0)}}
  whoosh — sahna kirishi/o'tish; hit — kuchli bass zarba (hook boshida, muhim tezis, brand boshida);
  blip — interfeysda elementlar paydo bo'lganda (ketma-ket 0.35 s oraliq, gain 0.5); swell — tarang ko'tarilish (eng muhim sahna boshida);
  glitch — cyber_outro oxirida (from:"end", offset:-0.55).
  Har videoda 5–12 ta sfx. Boshlanish: whoosh (0.0) + hit (0.35). Brand sahnasi: hit (offset 0.05, gain 0.8).
music_mood: dark (cyber/suspense), energetic, calm, inspiring. music_volume: 0.25–0.4 (dark: 0.28).
music_curve: [{{scene, gain}}] — eng muhim sahnada 1.3, xulosada 0.55–0.7. 2–3 element yetarli.

════════ 5. EKRAN MATNI ════════
- title/lines/l1: qisqa, zarbdor, KATTA HARF cyber'da; universalda odatiy yozuv. Emoji faqat generic shablonda va faqat emoji maydonida.
- Shaxsiy ma'lumot, real username/telefon/email ISHLATMA — faqat soxta namunalar (cyber_user01, user123@example.com, +998 ** *** ** **).
- caption_text: Instagram post tavsifi (3–5 qator + 6–10 hashtag, o'zbekcha).

════════ 6. NAMUNALAR (aynan shu sifat va tuzilma) ════════
--- Namuna A: cyber shablon, storyboard'dan yasalgan ---
{_example("cyber_01_hacker.json")}

--- Namuna B: universal shablon ---
{_example("ai_faktlar.json")}

Faqat JSON qaytar. Ishlatilmagan maydonlarga null qo'y."""


# ---------------------------------------------------------------- finalize
def _clean(o):
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items() if v is not None}
    if isinstance(o, list):
        return [_clean(v) for v in o]
    return o


def finalize(script: dict) -> dict:
    """Claude chiqargan rejani dvigatel formatiga keltiradi va xatolarni to'g'rilaydi."""
    s = _clean(script)
    s.setdefault("template", "template")
    s.setdefault("brand", BRAND["name"])
    s.setdefault("voice", "madina")
    s.setdefault("theme", "midnight")
    s.setdefault("music_mood", "inspiring")
    if s["music_mood"] == "dark":
        s.setdefault("music_file", MUSIC["dark"][0])
        s.setdefault("music_volume", 0.28)
    s.setdefault("captions", s["template"] != "cyber")
    # pronunciations: list -> dict
    pr = s.get("pronunciations") or []
    if isinstance(pr, list):
        s["pronunciations"] = {e["word"]: e["say"] for e in pr if e.get("word") and e.get("say")}
    # sahna turlari shablonga mos bo'lsin
    allowed = set(GENERIC_TYPES + ["brand"]) | (set(CYBER_TYPES) if s["template"] == "cyber" else set())
    scenes = [sc for sc in s.get("scenes", []) if sc.get("type") in allowed and sc.get("narration")]
    # brand doim oxirida, bitta
    brand = next((sc for sc in scenes if sc["type"] == "brand"), None) or {}
    scenes = [sc for sc in scenes if sc["type"] != "brand"]
    scenes.append({"type": "brand", "narration": brand.get("narration") or BRAND["narration"],
                   "cta": brand.get("cta") or BRAND["cta"], "sub": brand.get("sub") or BRAND["handle"], "min": 3.8,
                   **({"cut": "hard"} if s["template"] == "cyber" else {})})
    s["scenes"] = scenes
    # sfx / curve indekslari chegarada
    n = len(scenes)
    s["sfx"] = [e for e in s.get("sfx", []) if 0 <= int(e.get("scene", 0)) < n]
    s["music_curve"] = [e for e in s.get("music_curve", []) if 0 <= int(e.get("scene", 0)) < n]
    if not any(e.get("scene") == n - 1 for e in s["sfx"]):
        s["sfx"].append({"name": "hit", "scene": n - 1, "offset": 0.05, "gain": 0.8})
    return s


# ---------------------------------------------------------------- backendlar
def _user_msg(prompt, voice_hint, template_hint):
    user = prompt
    if voice_hint:
        user += f"\n\n(Ovoz: {voice_hint})"
    if template_hint and template_hint != "auto":
        user += f"\n\n(Shablon: {template_hint})"
    return user


def plan_via_cli(prompt: str, voice_hint: str | None = None, template_hint: str | None = None) -> dict:
    """Claude Code CLI (`claude -p`) orqali — obuna bilan, API kalitsiz."""
    exe = shutil.which("claude")
    if not exe:
        raise RuntimeError("`claude` CLI topilmadi")
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(SYSTEM); sys_file = f.name
    cmd = [exe, "-p", "--tools", "", "--no-session-persistence", "--output-format", "json",
           "--model", MODEL, "--effort", "high",
           "--system-prompt-file", sys_file, "--json-schema", json.dumps(SCHEMA),
           _user_msg(prompt, voice_hint, template_hint)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    finally:
        os.unlink(sys_file)
    if r.returncode != 0 and not r.stdout.strip():
        raise RuntimeError(f"claude CLI xato: {r.stderr.strip()[:500]}")
    data = json.loads(r.stdout)
    if data.get("is_error"):
        raise RuntimeError(f"claude CLI: {data.get('result')}")
    out = data.get("structured_output")
    if out is None:  # zaxira: matndan JSON ajratish
        txt = data.get("result", "").strip()
        if txt.startswith("```"):
            txt = txt.strip("`").split("\n", 1)[1] if "\n" in txt else txt
            txt = txt.rsplit("```", 1)[0]
        out = json.loads(txt)
    return finalize(out)


def plan_via_api(prompt: str, voice_hint: str | None = None, template_hint: str | None = None) -> dict:
    """Anthropic SDK orqali (ANTHROPIC_API_KEY)."""
    client = anthropic.Anthropic()
    user = _user_msg(prompt, voice_hint, template_hint)
    with client.beta.messages.stream(
        model=MODEL,
        max_tokens=32000,
        system=[{"type": "text", "text": SYSTEM, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
        thinking={"type": "adaptive"},
        output_config={"effort": "high", "format": {"type": "json_schema", "schema": SCHEMA}},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    ) as stream:
        resp = stream.get_final_message()

    if resp.stop_reason == "refusal":
        raise RuntimeError("Model so'rovni rad etdi (refusal). Promptni o'zgartirib ko'ring.")
    text = "".join(b.text for b in resp.content if b.type == "text")
    return finalize(json.loads(text))


def has_key() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def backend(prefer: str = "auto") -> str | None:
    """'api' | 'cli' | None — qaysi yo'l mavjud."""
    if prefer == "api":
        return "api" if has_key() else None
    if prefer == "cli":
        return "cli" if shutil.which("claude") else None
    if has_key():
        return "api"
    if shutil.which("claude"):
        return "cli"
    return None


def plan(prompt: str, voice_hint: str | None = None, template_hint: str | None = None, prefer: str = "auto") -> dict:
    b = backend(prefer)
    if b == "api":
        return plan_via_api(prompt, voice_hint, template_hint)
    if b == "cli":
        return plan_via_cli(prompt, voice_hint, template_hint)
    raise RuntimeError("Na ANTHROPIC_API_KEY, na `claude` CLI topilmadi")


if __name__ == "__main__":
    import sys
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    print(json.dumps(plan(" ".join(sys.argv[1:])), ensure_ascii=False, indent=1))
