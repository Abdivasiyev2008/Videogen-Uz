"""Oddiy ovoz effektlari (whoosh, bass hit, glitch, blip) — numpy bilan sintez."""
from __future__ import annotations
import wave
from pathlib import Path

import numpy as np

SR = 48000


def _env(n, a, d):
    """attack a sek, keyin eksponensial so'nish d sek."""
    t = np.arange(n) / SR
    att = np.clip(t / max(a, 1e-4), 0, 1)
    dec = np.exp(-np.maximum(t - a, 0) / max(d, 1e-4))
    return att * dec


def _lowpass(x, cutoff):
    rc = 1 / (2 * np.pi * cutoff)
    a = (1 / SR) / (rc + 1 / SR)
    y = np.empty_like(x); acc = 0.0
    for i, v in enumerate(x):
        acc += a * (v - acc); y[i] = acc
    return y


def whoosh(dur=1.1, seed=1):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    noise = rng.standard_normal(n)
    # ochilib-yopiladigan filtr: past->yuqori->past
    t = np.arange(n) / SR
    cut = 300 + 3500 * np.sin(np.pi * t / dur) ** 2
    y = np.empty(n); acc = 0.0
    for i in range(n):
        a = (1 / SR) / (1 / (2 * np.pi * cut[i]) + 1 / SR)
        acc += a * (noise[i] - acc); y[i] = acc
    y *= _env(n, dur * 0.45, dur * 0.25)
    return y / (np.abs(y).max() + 1e-9) * 0.8


def hit(dur=1.4):
    n = int(dur * SR); t = np.arange(n) / SR
    f = 38 + 70 * np.exp(-t * 9)
    ph = 2 * np.pi * np.cumsum(f) / SR
    y = np.sin(ph) * np.exp(-t * 2.2)
    click = np.random.default_rng(3).standard_normal(int(0.02 * SR)) * np.linspace(1, 0, int(0.02 * SR))
    y[: len(click)] += _lowpass(click, 4000) * 0.6
    return y / (np.abs(y).max() + 1e-9) * 0.95


def glitch(dur=0.55, seed=7):
    rng = np.random.default_rng(seed)
    n = int(dur * SR); y = np.zeros(n); pos = 0
    while pos < n - 100:
        seg = int(rng.uniform(0.02, 0.07) * SR); gap = int(rng.uniform(0.0, 0.03) * SR)
        seg = min(seg, n - pos)
        t = np.arange(seg) / SR
        if rng.random() < 0.5:
            fr = rng.uniform(200, 2500); s = np.sign(np.sin(2 * np.pi * fr * t)) * 0.5
        else:
            s = rng.standard_normal(seg) * 0.4
        y[pos:pos + seg] = s * np.linspace(1, 0.6, seg)
        pos += seg + gap
    return y * 0.9


def blip(dur=0.09, freq=1400):
    n = int(dur * SR); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * freq * t) * np.exp(-t * 45)
    return y * 0.5


def swell(dur=2.5):
    """past bass ko'tarilishi (rise)."""
    n = int(dur * SR); t = np.arange(n) / SR
    y = np.sin(2 * np.pi * 45 * t) * (t / dur) ** 2 * np.hanning(n) ** 0.3
    return y * 0.8


GEN = {"whoosh": whoosh, "hit": hit, "glitch": glitch, "blip": blip, "swell": swell}


def write_wav(path: Path, y: np.ndarray):
    y = np.clip(y, -1, 1)
    pcm = (np.stack([y, y], 1) * 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())


def make(name: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"sfx_{name}.wav"
    if not p.exists():
        write_wav(p, GEN[name]())
    return p


if __name__ == "__main__":
    for k in GEN:
        print(make(k, Path("out/_sfx")))
