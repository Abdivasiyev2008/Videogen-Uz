"""Inglizcha so'zlarni o'zbek TTS uchun fonetik yozuvga o'giradi (faqat ovoz uchun)."""
from __future__ import annotations
import json
import re
from pathlib import Path

DICT_PATH = Path(__file__).parent / "assets" / "pronounce.json"


def _load() -> list[tuple[re.Pattern, str]]:
    raw = json.loads(DICT_PATH.read_text())
    items = [(k.lower(), v) for k, v in raw.items() if not k.startswith("_")]
    items.sort(key=lambda kv: -len(kv[0]))  # uzun iboralar birinchi
    out = []
    for term, rep in items:
        # so'z boshida; oxirida o'zbekcha qo'shimcha bo'lishi mumkin (username'ni, hackerlar, emailga)
        pat = re.compile(r"(?<![\w'])" + re.escape(term).replace(r"\ ", r"\s+") + r"(?=(?:['ʼ’]?[a-z]*)?(?![\w]))", re.IGNORECASE)
        out.append((pat, rep))
    return out


_RULES = None


def _keep_case(src: str, rep: str) -> str:
    if src.isupper() and len(src) > 1:
        return rep.upper()
    if src[:1].isupper():
        return rep[:1].upper() + rep[1:]
    return rep


def _compile(term: str) -> re.Pattern:
    return re.compile(r"(?<![\w'])" + re.escape(term.lower()).replace(r"\ ", r"\s+") + r"(?=(?:['ʼ’]?[a-z]*)?(?![\w]))", re.IGNORECASE)


def for_tts(text: str, extra: dict | None = None) -> str:
    """Matnni ovoz sintezatoriga yuborishdan oldin talaffuzni tuzatadi. extra: skriptdagi qo'shimcha lug'at."""
    global _RULES
    if _RULES is None:
        _RULES = _load()
    rules = _RULES
    if extra:
        rules = [(_compile(k), v) for k, v in sorted(extra.items(), key=lambda kv: -len(kv[0]))] + rules
    for pat, rep in rules:
        text = pat.sub(lambda m: _keep_case(m.group(0), rep), text)
    return text


if __name__ == "__main__":
    import sys
    print(for_tts(" ".join(sys.argv[1:]) or "Cyber Security — faqat hacking emas. Bitta username orqali profilingiz, emailga bog'liq akkauntlar. Hackerlar phone number va old posts ni topadi."))
