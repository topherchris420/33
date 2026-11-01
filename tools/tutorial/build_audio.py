#!/usr/bin/env python3
"""Score, sound design and final mix for the tutorial film, synthesized offline.

    python tools/tutorial/build_audio.py              # build both cuts
    python tools/tutorial/build_audio.py --cut main   # one cut only

Reads build/tutorial/timeline.json (scenes, narration cues, events, sound cues)
and build/tutorial/narration/<cue>.wav. Writes:

    build/tutorial/audio/<cut>.wav                 float32 stereo masters
    build/tutorial/audio/stems/<cut>-{voice,music,sfx}.wav
    build/tutorial/audio/main-spectrogram.png
    assets/tutorial/tutorial-mix.m4a, assets/tutorial/preflight60-mix.m4a

Every sound is synthesized here with numpy/scipy: plucked strings
(Karplus-Strong), modal bars and tines, an additive felt piano, band-limited
saw pads, filtered-noise foley. No samples, no network, no API keys. All
randomness is seeded from the event it belongs to, so builds are identical.
"""
import argparse
import json
import re
import subprocess
import sys
import time
import zlib
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal
from scipy.ndimage import maximum_filter1d, minimum_filter1d, uniform_filter1d

ROOT = Path(__file__).resolve().parents[2]
TIMELINE = ROOT / "build" / "tutorial" / "timeline.json"
NARR = ROOT / "build" / "tutorial" / "narration"
OUT = ROOT / "build" / "tutorial" / "audio"
STEMS = OUT / "stems"
ASSETS = ROOT / "assets" / "tutorial"
M4A = {"main": "tutorial-mix.m4a", "preflight60": "preflight60-mix.m4a"}
SR = 48000

# Mix targets.
VOICE_LUFS = -16.5          # narration bus alone, before the master trim
MUSIC_LUFS = -20.5          # music bus alone, before ducking
TARGET_LUFS = -16.0         # final integrated loudness
CEILING_DBTP = -1.6         # limiter ceiling (leaves room for AAC overshoot)
DUCK_DB_MUSIC = -9.5
DUCK_DB_SFX = -4.0


# ════════════════════════════════════════════════════════════════════════════
# DSP helpers
# ════════════════════════════════════════════════════════════════════════════

def seed(*parts):
    return zlib.crc32(repr(parts).encode())


def rng_for(*parts):
    return np.random.default_rng(seed(*parts))


def db(x):
    return 20 * np.log10(np.maximum(np.abs(x), 1e-12))


def undb(d):
    return 10 ** (d / 20)


_SOS = {}


def sos(kind, fc, order=2):
    key = (kind, tuple(np.atleast_1d(fc)), order)
    if key not in _SOS:
        _SOS[key] = signal.butter(order, fc, btype=kind, fs=SR, output="sos")
    return _SOS[key]


def lp(x, fc, order=2):
    return signal.sosfilt(sos("lowpass", min(fc, SR * 0.45), order), x, axis=0)


def hp(x, fc, order=2):
    return signal.sosfilt(sos("highpass", fc, order), x, axis=0)


def bp(x, lo, hi, order=2):
    return signal.sosfilt(sos("bandpass", (lo, min(hi, SR * 0.45)), order), x, axis=0)


def peaking(x, f0, gain_db, q):
    """RBJ peaking EQ."""
    a = 10 ** (gain_db / 40)
    w = 2 * np.pi * f0 / SR
    al = np.sin(w) / (2 * q)
    b = [1 + al * a, -2 * np.cos(w), 1 - al * a]
    aa = [1 + al / a, -2 * np.cos(w), 1 - al / a]
    return signal.lfilter(np.array(b) / aa[0], np.array(aa) / aa[0], x, axis=0)


def resonate(x, f0, q):
    b, a = signal.iirpeak(f0, q, fs=SR)
    return signal.lfilter(b, a, x)


def tv_bandpass(x, fc, q=1.0, block=128):
    """Band-pass with a time-varying centre (per-sample array fc), block-wise."""
    y = np.zeros_like(x)
    zi = np.zeros(2)
    for i in range(0, len(x), block):
        f0 = float(np.clip(fc[min(i + block // 2, len(fc) - 1)], 40, SR * 0.42))
        w = 2 * np.pi * f0 / SR
        al = np.sin(w) / (2 * q)
        b = np.array([al, 0, -al]) / (1 + al)
        a = np.array([1, -2 * np.cos(w) / (1 + al), (1 - al) / (1 + al)])
        y[i:i + block], zi = signal.lfilter(b, a, x[i:i + block], zi=zi)
    return y


def tvec(n):
    return np.arange(n) / SR


def ns(sec):
    return max(1, int(round(sec * SR)))


def fade(x, a=0.002, r=0.01):
    x = x.copy()
    na, nr = min(len(x), ns(a)), min(len(x), ns(r))
    x[:na] *= np.sin(np.linspace(0, np.pi / 2, na)) ** 2
    x[len(x) - nr:] *= np.cos(np.linspace(0, np.pi / 2, nr)) ** 2
    return x


def edecay(n, tau):
    return np.exp(-tvec(n) / tau)


def t60env(n, t60):
    return 10 ** (-3 * tvec(n) / t60)


def pan_gains(p):
    p = float(np.clip(p, -1, 1))
    th = (p + 1) * np.pi / 4
    return np.array([np.cos(th), np.sin(th)]) * np.sqrt(2)


def add(buf, x, t, pan=0.0, gain=1.0):
    """Mix mono (pan applied) or stereo x into stereo buf at time t."""
    i0 = int(round(t * SR))
    if i0 >= len(buf):
        return
    if x.ndim == 1:
        x = x[:, None] * pan_gains(pan)[None, :]
    if i0 < 0:
        x, i0 = x[-i0:], 0
    n = min(len(x), len(buf) - i0)
    buf[i0:i0 + n] += gain * x[:n]


def noise(rng, n):
    return rng.standard_normal(n)


# ── BS.1770 loudness (K-weighting, gating) ─────────────────────────────────
KW1 = ([1.53512485958697, -2.69169618940638, 1.19839281085285],
       [1.0, -1.69065929318241, 0.73248077421585])
KW2 = ([1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621])


def kpower(x):
    """K-weighted power summed over channels, per sample."""
    x = x if x.ndim == 2 else x[:, None]
    y = signal.lfilter(*KW1, x, axis=0)
    y = signal.lfilter(*KW2, y, axis=0)
    return (y ** 2).sum(axis=1)


def window_lufs(p, win, hop):
    W, H = ns(win), ns(hop)
    cs = np.concatenate([[0.0], np.cumsum(p)])
    starts = np.arange(0, max(1, len(p) - W + 1), H)
    ms = (cs[np.minimum(starts + W, len(p))] - cs[starts]) / W
    return starts, -0.691 + 10 * np.log10(np.maximum(ms, 1e-20))


def integrated_lufs(x):
    p = kpower(x)
    _, L = window_lufs(p, 0.4, 0.1)
    L = L[L > -70]
    if len(L) == 0:
        return -120.0
    rel = -0.691 + 10 * np.log10(np.mean(10 ** ((L + 0.691) / 10))) - 10
    L = L[L > rel]
    return float(-0.691 + 10 * np.log10(np.mean(10 ** ((L + 0.691) / 10))))


def momentary_max(x):
    p = kpower(x)
    if len(p) < ns(0.4):
        p = np.concatenate([p, np.zeros(ns(0.4) - len(p))])
    _, L = window_lufs(p, 0.4, 0.01)
    return float(L.max())


def true_peak_db(x):
    os_ = signal.resample_poly(x, 4, 1, axis=0)
    return float(db(np.abs(os_).max()))


# ── Reverb: exponentially decaying noise IR, frequency-dependent decay ─────
def make_ir(rt60, length, seed_, predelay=0.012, er=True):
    rng = np.random.default_rng(seed_)
    n = ns(length)
    t = tvec(n)
    ir = np.zeros((n + ns(predelay), 2))
    for ch in range(2):
        w = rng.standard_normal(n)
        lo = lp(w, 500)
        hi = hp(w, 4000)
        mid = w - lo - hi
        env = lambda r: 10 ** (-3 * t / r)
        x = 1.2 * lo * env(rt60 * 1.15) + mid * env(rt60) + 0.6 * hi * env(rt60 * 0.45)
        x *= 1 - np.exp(-t / 0.006)
        if er:
            for d, g in [(0.0071, 0.6), (0.0113, -0.45), (0.0167, 0.38), (0.0229, -0.3), (0.0311, 0.22)]:
                k = ns(d * (1 + 0.07 * ch))
                x[k] += g * 3
        ir[ns(predelay):, ch] = x
    ir /= np.sqrt((ir ** 2).sum(axis=0, keepdims=True))
    return ir


def convolve_st(x, ir):
    out = np.zeros_like(x)
    for ch in range(2):
        out[:, ch] = signal.oaconvolve(x[:, ch], ir[:, ch])[:len(x)]
    return out


# ════════════════════════════════════════════════════════════════════════════
# Pitch helpers
# ════════════════════════════════════════════════════════════════════════════
PC = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6,
      "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}


def nm(name):
    m = re.fullmatch(r"([A-G][#b]?)(-?\d)", name)
    if not m:
        raise ValueError(name)
    return 12 * (int(m.group(2)) + 1) + PC[m.group(1)]


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


QUAL = {"": [0, 4, 7], "m": [0, 3, 7], "7": [0, 4, 7, 10], "maj7": [0, 4, 7, 11],
        "m7": [0, 3, 7, 10], "sus4": [0, 5, 7], "7sus4": [0, 5, 7, 10], "sus2": [0, 2, 7],
        "add9": [0, 4, 7, 14], "maj9": [0, 4, 7, 11, 14], "m9": [0, 3, 7, 10, 14],
        "6": [0, 4, 7, 9], "m11": [0, 3, 7, 10, 17]}


def chord(sym):
    m = re.fullmatch(r"([A-G][#b]?)([^/]*)(?:/([A-G][#b]?))?", sym)
    root = PC[m.group(1)]
    ivs = QUAL[m.group(2)]
    bass = PC[m.group(3)] if m.group(3) else root
    return root, ivs, bass


def voicing(sym, lo):
    root, ivs, _ = chord(sym)
    out = []
    for iv in ivs:
        pc = (root + iv) % 12
        p = lo + ((pc - lo) % 12)
        if iv >= 12:
            p += 12 if p < lo + 12 else 0
        out.append(p)
    return sorted(set(out))


def bass_of(sym, lo=38):
    _, _, b = chord(sym)
    return lo + ((b - lo) % 12)


D_MAJOR = {2, 4, 6, 7, 9, 11, 1}
PENTA = [2, 4, 6, 9, 11]          # D major / B minor pentatonic


def penta_from(start, k):
    """k-th pentatonic pitch at or above MIDI note `start`."""
    out, p = [], start
    while len(out) <= k:
        if p % 12 in PENTA:
            out.append(p)
        p += 1
    return out[k]


# ════════════════════════════════════════════════════════════════════════════
# Instruments (each returns a mono or stereo float array starting at onset)
# ════════════════════════════════════════════════════════════════════════════

def ks_string(f, dur, t60, bright, rng, pos=0.18, bend=None):
    """Karplus-Strong at an internal rate where the loop length is exact."""
    N = max(4, int(SR / f))
    srp = f * (N + 0.5)                     # the averaging filter adds half a sample
    L = int((dur + 0.05) * srp) + 2 * N + 2
    y = np.zeros(L + 1)
    exc = rng.standard_normal(N)
    a = float(np.clip(1 - bright, 0.0, 0.97))
    exc = signal.lfilter([1 - a], [1, -a], exc)
    k = max(1, int(pos * N))
    exc = exc - 0.9 * np.roll(exc, k)
    exc -= exc.mean()
    exc /= np.abs(exc).max() + 1e-12
    y[1:N + 1] = exc
    rho = 10 ** (-3.0 / (t60 * f))
    for a0 in range(N + 1, L + 1, N):
        b0 = min(a0 + N, L + 1)
        y[a0:b0] = rho * 0.5 * (y[a0 - N:b0 - N] + y[a0 - N - 1:b0 - N - 1])
    y = y[1:]
    nout = ns(dur)
    step = np.full(nout, srp / SR)
    if bend is not None:
        step *= bend[:nout]
    pos_ = np.concatenate([[0.0], np.cumsum(step)[:-1]])
    return np.interp(pos_, np.arange(len(y)), y)


_PIZZ_BODY = None


def syn_pizz(f, dur, vel, rng, **_):
    t60 = float(np.clip(0.8 * (330 / f) ** 0.45, 0.32, 1.5))
    length = t60 * 0.85 + 0.05
    y = ks_string(f, length, t60, 0.3 + 0.35 * vel, rng, pos=0.13)
    body = (y + 0.9 * resonate(y, 275, 3) + 0.6 * resonate(y, 510, 4)
            + 0.35 * resonate(y, 1150, 3) + 0.15 * resonate(y, 2700, 3))
    body = lp(body, 4200)
    thump = lp(noise(rng, ns(0.006)), 900) * 0.15 * vel
    body[:len(thump)] += thump
    body /= np.abs(body).max() + 1e-12
    return fade(body, 0.0015, 0.04) * vel ** 1.3


def syn_bass(f, dur, vel, rng, slide=0.0, **_):
    length = min(dur + 0.2, 2.6)
    n = ns(length)
    t = tvec(n)
    bend = None
    if slide:
        bend = 2 ** ((-slide * np.exp(-t / 0.05)) / 12)
    y = ks_string(f, length, 1.9, 0.16 + 0.14 * vel, rng, pos=0.28, bend=bend)
    y /= np.abs(y[:ns(0.05)]).max() + 1e-12
    ph = 2 * np.pi * np.cumsum(f * (bend if bend is not None else 1.0) * np.ones(n)) / SR
    y += 0.45 * np.sin(ph) * np.exp(-t / 0.45) * (1 - np.exp(-t / 0.004))
    y = lp(y, 1000)
    y = peaking(y, 120, 2.0, 0.8)
    # player damps the string at the written end
    d = ns(max(0.05, dur))
    if d < n:
        r = np.ones(n)
        rl = min(n - d, ns(0.14))
        r[d:d + rl] = np.cos(np.linspace(0, np.pi / 2, rl)) ** 2
        r[d + rl:] = 0
        y *= r
    y /= np.abs(y).max() + 1e-12
    return fade(y, 0.002, 0.03) * vel ** 1.2


def modal(f, parts, n, rng):
    t = tvec(n)
    out = np.zeros(n)
    for ratio, amp, t60 in parts:
        fr = f * ratio
        if fr > 19000 or amp <= 0:
            continue
        out += amp * np.sin(2 * np.pi * fr * t) * 10 ** (-3 * t / t60)
    return out


def syn_marimba(f, dur, vel, rng, damp=False, **_):
    t60 = float(np.clip(1.5 * (262 / f) ** 0.6, 0.3, 2.2))
    if damp:
        t60 *= 0.3
    n = ns(min(t60 + 0.05, 2.6))
    y = modal(f, [(1, 1.0, t60), (3.98, 0.22 * (0.4 + vel), t60 * 0.22),
                  (9.9, 0.06 * vel, t60 * 0.08)], n, rng)
    m = lp(noise(rng, ns(0.004)), 2500) * edecay(ns(0.004), 0.0012) * 0.12 * vel
    y[:len(m)] += m
    y *= 1 - np.exp(-tvec(n) / 0.0012)
    return fade(y / (np.abs(y).max() + 1e-12), 0.0005, 0.03) * vel ** 1.3


def syn_vibes(f, dur, vel, rng, trem=3.4, **_):
    t60 = float(np.clip(4.2 * (262 / f) ** 0.4, 1.6, 5.0))
    length = min(dur, t60) + 0.35
    n = ns(length)
    t = tvec(n)
    y = modal(f, [(1, 1.0, t60), (4.0, 0.09 * (0.5 + vel), t60 * 0.15),
                  (10.0, 0.025 * vel, t60 * 0.05)], n, rng)
    y *= 1 - 0.24 * (0.5 - 0.5 * np.cos(2 * np.pi * trem * t + rng.uniform(0, 6.28)))
    y *= 1 - np.exp(-t / 0.0025)
    d = ns(dur)
    if d < n:
        rel = np.ones(n)
        rl = n - d
        rel[d:] = np.cos(np.linspace(0, np.pi / 2, rl)) ** 2
        y *= rel
    return fade(y / (np.abs(y).max() + 1e-12), 0.002, 0.03) * vel ** 1.3


def syn_mbox(f, dur, vel, rng, **_):
    t60 = float(np.clip(2.2 * (880 / f) ** 0.5, 0.8, 3.0))
    n = ns(t60 + 0.05)
    t = tvec(n)
    y = modal(f, [(1, 1.0, t60), (1.0018, 0.16, t60 * 0.9), (2.0, 0.07, t60 * 0.4),
                  (6.27, 0.22, 0.16), (17.55, 0.07, 0.045)], n, rng)
    c = hp(noise(rng, ns(0.0015)), 3000) * 0.08
    y[:len(c)] += c
    y *= 1 - np.exp(-t / 0.0006)
    return fade(y / (np.abs(y).max() + 1e-12), 0.0003, 0.05) * vel ** 1.2


def syn_piano(f, dur, vel, rng, **_):
    """Felt piano: stretched partials, soft hammer, two strings per partial."""
    length = min(dur + 0.45, 6.5)
    n = ns(length)
    t = tvec(n)
    B = 0.00022 * (f / 262) ** 0.5
    N = int(max(3, min(14, 4800 / f)))
    y = np.zeros(n)
    bright = 700 + 1100 * vel
    for k in range(1, N + 1):
        fk = f * k * np.sqrt(1 + B * k * k)
        ak = (1 / k ** (1.5 - 0.5 * vel)) / (1 + (fk / bright) ** 2)
        tau1 = float(np.clip(0.55 * (262 / fk) ** 0.55, 0.05, 2.2))
        tau2 = tau1 * 5.0
        env = 0.62 * np.exp(-t / tau1) + 0.38 * np.exp(-t / tau2)
        det = fk * 0.00035
        ph = rng.uniform(0, 6.28)
        y += ak * env * 0.5 * (np.sin(2 * np.pi * (fk - det) * t + ph)
                               + np.sin(2 * np.pi * (fk + det) * t + ph * 0.7))
    y *= 1 - np.exp(-t / 0.004)
    h = lp(noise(rng, ns(0.03)), 420) * edecay(ns(0.03), 0.01) * 0.05 * vel
    y[:len(h)] += h
    d = ns(dur)
    if d < n:
        rel = np.ones(n)
        rl = min(n - d, ns(0.35))
        rel[d:d + rl] = np.cos(np.linspace(0, np.pi / 2, rl)) ** 2
        rel[d + rl:] = 0
        y *= rel
    return fade(y / (np.abs(y).max() + 1e-12), 0.001, 0.05) * vel ** 1.25


def saw_blep(freq):
    dt = freq / SR
    ph = np.cumsum(dt) % 1.0
    s = 2 * ph - 1
    m1 = ph < dt
    tt = ph[m1] / dt[m1]
    s[m1] -= tt + tt - tt * tt - 1
    m2 = ph > 1 - dt
    tt = (ph[m2] - 1) / dt[m2]
    s[m2] -= tt * tt + tt + tt + 1
    return s


def syn_pad(f, dur, vel, rng, attack=1.1, release=1.6, cutoff=None, **_):
    length = dur + release
    n = ns(length)
    t = tvec(n)
    drift = 1 + 0.0011 * np.sin(2 * np.pi * 0.17 * t + rng.uniform(0, 6.28))
    out = np.zeros((n, 2))
    for cents, p in ((-9, -0.65), (0, 0.0), (8, 0.65)):
        s = saw_blep(f * 2 ** (cents / 1200) * drift * np.ones(n))
        out += s[:, None] * pan_gains(p)[None, :] * 0.4
    out += (0.35 * np.sin(2 * np.pi * f * t))[:, None]
    fc = cutoff or (620 + 650 * vel)
    out = lp(out, fc, 2)
    out = lp(out, fc * 2.2, 1)
    env = np.ones(n)
    na, nd = ns(attack), ns(dur)
    env[:na] = np.sin(np.linspace(0, np.pi / 2, na)) ** 2
    nr = n - nd
    if nr > 0:
        env[nd:] = env[nd - 1] * np.cos(np.linspace(0, np.pi / 2, nr)) ** 2
    out *= env[:, None]
    return out / (np.abs(out).max() + 1e-12) * vel ** 1.1


def syn_brush(f, dur, vel, rng, period=1.3, **_):
    """Brushed-snare swirl: a soft wire-brush circle on a drum head."""
    n = ns(dur)
    t = tvec(n)
    w = np.stack([noise(rng, n), noise(rng, n)], axis=1)
    w = bp(w, 2200, 8500)
    sw = 0.3 + 0.7 * (0.5 - 0.5 * np.cos(2 * np.pi * t / period + rng.uniform(0, 1))) ** 1.5
    g = np.ones(n)
    k = min(n // 2, ns(0.5))
    g[:k] = np.linspace(0, 1, k)
    g[n - k:] = np.linspace(1, 0, k)
    return w * (sw * g)[:, None] * 0.3 * vel


def syn_tap(f, dur, vel, rng, **_):
    n = ns(0.2)
    t = tvec(n)
    x = bp(noise(rng, n), 1300, 6500) * np.exp(-t / 0.045) * (1 - np.exp(-t / 0.003))
    x += 0.25 * np.sin(2 * np.pi * 185 * t) * np.exp(-t / 0.03)
    return fade(x / (np.abs(x).max() + 1e-12), 0.001, 0.02) * vel


def syn_tw(f, dur, vel, rng, **_):
    """A tiny typewriter key: a dry clack with a small metallic resonance."""
    n = ns(0.05)
    t = tvec(n)
    c = np.zeros(n)
    c[:ns(0.001)] = hp(noise(rng, ns(0.001)), 2000)
    x = resonate(c, 3300 * rng.uniform(0.93, 1.07), 6) + 0.4 * c
    k = ns(0.009)
    x[k:] += 0.45 * resonate(c, 1800, 5)[:n - k]
    return fade(x / (np.abs(x).max() + 1e-12), 0.0002, 0.01) * vel


# name: (synth, gain dB, reverb send, default pan)
INST = {
    "pizz":    (syn_pizz,    -1.0, 0.28, -0.25),
    "pizzmid": (syn_pizz,    -6.0, 0.28, 0.22),
    "bass":    (syn_bass,     0.0, 0.12, 0.0),
    "marimba": (syn_marimba, -4.0, 0.30, 0.30),
    "vibes":   (syn_vibes,   -6.0, 0.36, -0.2),
    "mbox":    (syn_mbox,    -8.0, 0.42, 0.15),
    "piano":   (syn_piano,   -1.0, 0.50, 0.0),
    "pad":     (syn_pad,    -12.0, 0.30, 0.0),
    "brush":   (syn_brush,  -21.0, 0.15, 0.1),
    "tap":     (syn_tap,    -23.0, 0.15, 0.1),
    "tw":      (syn_tw,     -27.0, 0.10, -0.3),
}


# ════════════════════════════════════════════════════════════════════════════
# Score notation
# ════════════════════════════════════════════════════════════════════════════

class Score:
    def __init__(self, name):
        self.name = name
        self.ev = []

    def note(self, inst, t, midi, dur, vel, pan=None, human=True, **kw):
        r = rng_for(self.name, inst, round(t, 4), midi)
        if human:
            t += r.uniform(-0.007, 0.007)
            vel *= r.uniform(0.94, 1.04)
        self.ev.append(dict(inst=inst, t=float(t), midi=midi, dur=float(dur),
                            vel=float(np.clip(vel, 0.02, 1.0)), pan=pan, kw=kw))


class Sec:
    """A stretch of music on a beat grid: bar 1 beat 0 is at t0."""

    def __init__(self, S, t0, bpm, bpb=4):
        self.S, self.t0, self.b, self.bpb = S, t0, 60.0 / bpm, bpb

    def T(self, bar, beat=0.0):
        return self.t0 + ((bar - 1) * self.bpb + beat) * self.b

    def mel(self, inst, text, bar=1, beat=0.0, vel=0.5, pan=None, legato=0.95,
            transpose=0, accent=0.12, **kw):
        pos = (bar - 1) * self.bpb + beat
        for tok in text.split():
            if tok == "|":
                continue
            name, d = tok.split(":")
            d = float(d)
            if name != "r":
                v = vel * (1 + accent if abs(pos % self.bpb) < 1e-6 else 1.0)
                self.S.note(inst, self.t0 + pos * self.b, nm(name) + transpose,
                            d * self.b * legato, v, pan, **kw)
            pos += d

    def chord(self, inst, sym, bar, beat, beats, vel, lo, roll=0.0, pan=None, **kw):
        for i, m in enumerate(voicing(sym, lo)):
            self.S.note(inst, self.T(bar, beat) + i * roll, m, beats * self.b, vel, pan, **kw)

    def bass(self, sym, bar, beat, beats, vel, slide=0.0, midi=None):
        m = midi if midi is not None else bass_of(sym)
        self.S.note("bass", self.T(bar, beat), m, beats * self.b * 0.92, vel, slide=slide)


def bars(prog):
    """'D | A7sus4 A7 | G' -> [[(sym, beat0, beats)], ...] assuming 4/4."""
    out = []
    for cell in prog.split("|"):
        syms = cell.split()
        w = 4 / len(syms)
        out.append([(s, i * w, w) for i, s in enumerate(syms)])
    return out


def chord_pcs(sym):
    root, ivs, _ = chord(sym)
    return [(root + iv) % 12 for iv in ivs]


def walk_tones(sym):
    """Chord tones from the bass note upward, within an octave."""
    r = bass_of(sym)
    return sorted({r + ((pc - r) % 12) for pc in chord_pcs(sym)})


def alt_bass(sym):
    """The 'pah' of an oom-pah: the fifth below, or the root under a slash chord."""
    root, _, b = chord(sym)
    r = bass_of(sym)
    pc = root if b != root else (root + 7) % 12
    cand = r - ((r - pc) % 12)
    if cand == r:
        cand -= 12
    return cand + 12 if cand < 33 else cand


def approach(cur, nxt):
    """Diatonic step into the next bass note."""
    below = nxt - 1 if (nxt - 1) % 12 in D_MAJOR else nxt - 2
    above = nxt + 1 if (nxt + 1) % 12 in D_MAJOR else nxt + 2
    return below if abs(below - cur) <= abs(above - cur) else above


def accompany(sec, prog, style, vel=0.5, first_bar=1, next_after=None, skip=()):
    """Bass + mid pizz accompaniment under a chord progression."""
    cells = bars(prog)
    flat = [c for cell in cells for c in cell]
    for bi, cell in enumerate(cells):
        bar = first_bar + bi
        if bar in skip:
            continue
        for ci, (sym, b0, nb) in enumerate(cell):
            idx = flat.index((sym, b0, nb), sum(len(c) for c in cells[:bi]))
            nxt = flat[idx + 1][0] if idx + 1 < len(flat) else (next_after or sym)
            r = bass_of(sym)
            fifth = alt_bass(sym)
            tones = voicing(sym, 55)
            if style == "oompah":
                sec.bass(sym, bar, b0, min(2, nb), vel * 0.95, slide=0.3 if b0 == 0 and bar % 3 == 1 else 0)
                if nb >= 4:
                    sec.bass(sym, bar, b0 + 2, 2, vel * 0.8, midi=fifth)
                for k in (1, 3):
                    if k < b0 + nb and k >= b0:
                        for j, m in enumerate(tones[:3]):
                            sec.S.note("pizzmid", sec.T(bar, k) + j * 0.012, m, 0.3, vel * 0.7)
            elif style == "walk":
                wt = walk_tones(sym) + [r + 12]
                line = [r, wt[1], wt[2], approach(wt[2], bass_of(nxt))]
                for k in range(int(nb)):
                    sec.bass(sym, bar, b0 + k, 0.9, vel * (0.95 if k == 0 else 0.78),
                             midi=line[k] if nb >= 4 else (r if k == 0 else fifth),
                             slide=0.35 if k == 0 and bar % 4 == 1 else 0)
                cyc = [tones[-1], tones[1 % len(tones)], tones[-1], tones[0]]
                for k in range(int(nb)):
                    sec.S.note("pizzmid", sec.T(bar, b0 + k + 0.5), cyc[k % 4], 0.25, vel * 0.62)
            elif style == "half":
                sec.bass(sym, bar, b0, min(2, nb), vel * 0.9)
                if nb >= 4:
                    sec.bass(sym, bar, b0 + 2, 2, vel * 0.75, midi=fifth)
                for j, m in enumerate(tones[:3]):
                    sec.S.note("pizzmid", sec.T(bar, b0 + 1) + j * 0.015, m, 0.3, vel * 0.55)
            elif style == "roots":
                sec.bass(sym, bar, b0, nb, vel * 0.85)


def arp8(sec, inst, prog, first_bar, vel, lo, pattern=(0, 1, 2, 1, 3, 1, 2, 1), skip=()):
    for bi, cell in enumerate(bars(prog)):
        bar = first_bar + bi
        if bar in skip:
            continue
        for sym, b0, nb in cell:
            tones = voicing(sym, lo)
            tones = tones + [tones[0] + 12]
            for k in range(int(nb * 2)):
                m = tones[pattern[k % len(pattern)] % len(tones)]
                sec.S.note(inst, sec.T(bar, b0 + k * 0.5), m, 0.4, vel * (1.1 if k == 0 else 1.0))


def pads(sec, prog, first_bar, vel, lo=50, overlap=0.35, **kw):
    for bi, cell in enumerate(bars(prog)):
        for sym, b0, nb in cell:
            for m in voicing(sym, lo):
                sec.S.note("pad", sec.T(first_bar + bi, b0), m, nb * sec.b + overlap, vel,
                           human=False, **kw)


def brushes(sec, bar0, bar1, vel=1.0, taps=True, tw=0.2, swirl=True):
    S = sec.S
    if swirl:
        S.note("brush", sec.T(bar0), 0, (bar1 - bar0 + 1) * sec.bpb * sec.b + 0.3, vel,
               human=False, period=2 * sec.b)
    r = rng_for(S.name, "tw", round(sec.t0, 3), bar0)
    for bar in range(bar0, bar1 + 1):
        if taps:
            for k in (1, 3):
                S.note("tap", sec.T(bar, k), 0, 0.2, 0.8 * vel)
        if tw > 0:
            for k in range(16):
                if k % 4 != 0 and r.random() < tw:
                    S.note("tw", sec.T(bar, k * 0.25), 0, 0.05, vel * r.uniform(0.5, 1.0))


# ── Themes ──────────────────────────────────────────────────────────────────
THEME_A = "D | A/C# | Bm | G | D/F# | G | Em7 | A7"
THEME_A_MEL = """
D5:0.5 F#5:0.5 A5:1 F#5:0.5 E5:0.5 D5:1 | E5:0.5 C#5:0.5 A4:1 E5:1 r:1 |
F#5:0.5 D5:0.5 B4:1 D5:0.5 F#5:0.5 B5:1 | A5:1.5 G5:0.5 D5:1 r:1 |
A5:0.5 F#5:0.5 D5:1 F#5:0.5 A5:0.5 D6:1 | B5:1 G5:0.5 B5:0.5 D6:1 r:1 |
G5:0.5 F#5:0.5 E5:0.5 D5:0.5 E5:1 B4:1 | C#5:1 E5:0.5 A5:0.5 G5:1 r:1
"""
THEME_B = "Bm | F#m | G | D | Em | Bm/D | A | A7"
THEME_B_MEL = """
F#5:1 B5:1 A5:0.5 F#5:0.5 D5:1 | C#5:1 F#5:1 E5:0.5 C#5:0.5 A4:1 |
B4:0.5 D5:0.5 G5:1 F#5:0.5 E5:0.5 D5:1 | A4:0.5 D5:0.5 F#5:1 A5:2 |
G5:0.5 E5:0.5 B4:1 E5:0.5 G5:0.5 B5:1 | A5:0.5 F#5:0.5 D5:1 F#5:1 r:1 |
E5:1 C#5:0.5 E5:0.5 A5:1 G5:1 | F#5:0.5 E5:0.5 C#5:0.5 A4:0.5 E5:1 r:1
"""
COVER = "Dadd9 | Gmaj7 | Bm7 | A7sus4 A7 | Gmaj7 | A7 D"
COVER_MEL = """
A5:1 F#5:0.5 A5:0.5 D6:2 | B5:1 A5:0.5 F#5:0.5 D5:2 | F#5:1 E5:0.5 F#5:0.5 B5:2 |
A5:1 G5:0.5 E5:0.5 C#5:1 E5:1 | D5:0.5 F#5:0.5 B5:1 A5:1 F#5:1 | E5:1 A4:1 D5:2
"""


def mel_bars(text, i0, i1):
    cells = [c for c in text.replace("\n", " ").split("|") if c.strip()]
    return " | ".join(cells[i0:i1])


def prog_bars(prog, i0, i1):
    return " | ".join(prog.split("|")[i0:i1])


# ════════════════════════════════════════════════════════════════════════════
# Score: main cut
# ════════════════════════════════════════════════════════════════════════════

def cue(cut, cid):
    return next(c for c in cut["cues"] if c["id"] == cid)


def drop_window(cut):
    return cue(cut, "s5h")["start"] - 0.25, cue(cut, "s5i")["end"] + 0.2


def preflight_block(S, t0, nbars_a, drop, post_t):
    """Shared by both cuts: theme A, then theme B up to the press, a held
    suspension, silence for 'It refuses. ... Good.', then a small cadence."""
    sec = Sec(S, t0, 92)
    full = THEME_A + " | " + prog_bars(THEME_B, 0, 4)
    fullm = THEME_A_MEL + " | " + mel_bars(THEME_B_MEL, 0, 4)
    prog = prog_bars(full, 0, nbars_a)
    melo = mel_bars(fullm, 0, nbars_a)
    S.note("pizz", sec.T(0, 3.5), nm("A4"), 0.3, 0.4)            # pickup
    sec.mel("pizz", melo, 1, vel=0.62)
    sec.mel("marimba", mel_bars(fullm, 4, min(8, nbars_a)), 5, vel=0.36, transpose=-12)
    if nbars_a > 8:
        sec.mel("marimba", mel_bars(fullm, 8, nbars_a), 9, vel=0.34)
    accompany(sec, prog, "walk", vel=0.55, next_after="A")
    brushes(sec, 1, nbars_a, vel=1.0, tw=0.22)
    # the held question: "Ask the dashboard to launch..."
    hb = nbars_a + 1
    hold = drop[0] - sec.T(hb) - 0.15
    sec.chord("vibes", "A7sus4", hb, 0, hold / sec.b, 0.42, 57, roll=0.02)
    sec.bass("A7sus4", hb, 0, hold / sec.b, 0.45)
    for m in voicing("A7sus4", 50):
        S.note("pad", sec.T(hb), m, hold - 0.6, 0.35, human=False, release=0.5, attack=0.4)
    for k, m in enumerate(["E4", "A4", "D5", "E5"]):
        S.note("pizzmid", sec.T(hb, k * 0.5), nm(m), 0.3, 0.4)
    # "Good." -- a small, pleased cadence
    post = Sec(S, post_t, 92)
    post.bass("D", 1, 0, 3, 0.55, slide=0.3)
    post.mel("pizz", "A4:0.5 D5:0.5 F#5:0.5 A5:0.5 D6:1", 1, vel=0.5)
    post.chord("vibes", "Dadd9", 1, 0, 4, 0.38, 57, roll=0.03)
    post.S.note("mbox", post.T(1, 3), nm("D6"), 1.0, 0.35)
    return sec


def score_main(cut):
    S = Score("main")
    ev = cut["events"]
    cues = {c["id"]: c for c in cut["cues"]}

    # ── cover (0-19): vibes chords, music-box melody, bass enters bar 3 ──
    t0 = ev["s1.lampOn"]
    bpm = 60 / ((ev["s1.stampHit"] - t0) / 22)            # beat 22 lands on the stamp
    cov = Sec(S, ev["s1.stampHit"] - 22 * 60 / bpm, bpm)
    for bi, cell in enumerate(bars(COVER)):
        for sym, b0, nb in cell:
            cov.chord("vibes", sym, bi + 1, b0, nb, 0.34 if bi else 0.28, 57, roll=0.03 if bi == 0 else 0.0)
            if bi >= 2:
                cov.bass(sym, bi + 1, b0, nb, 0.4)
    cov.mel("mbox", COVER_MEL, 1, vel=0.5, legato=1.0)
    cov.mel("marimba", "r:2 D5:0.5 E5:0.5 F#5:1 | r:2 C#5:1 E5:1", 5, vel=0.25)
    cov.chord("vibes", "D", 7, 0, 3, 0.25, 62)

    # ── toc (19-32.5): a marimba note for each leader line, then spare ──
    leads = [ev[f"s2.lead{i}"] for i in range(9)]
    for t, m in zip(leads, ["D4", "E4", "F#4", "G4", "A4", "B4", "C#5", "D5", "E5"]):
        S.note("marimba", t, nm(m), 0.4, 0.4)
    toc = Sec(S, leads[0], 120)
    toc.chord("vibes", "Dmaj7", 1, 0, 4, 0.26, 57)
    toc.chord("vibes", "Gmaj7", 2, 0, 4, 0.24, 57)
    toc.bass("D", 1, 0, 3, 0.4)
    toc.bass("G", 2, 0, 3, 0.36)
    # under "Flight characteristics: not measured." -- one held, open chord
    for m in ("A3", "B3", "E4"):                     # under s2a: one open, held chord
        S.note("vibes", leads[8], nm(m), 3.0, 0.2)
    for m in ("G3", "B3", "E4"):                     # under s2b: barely moves
        S.note("vibes", cues["s2b"]["start"] - 0.2, nm(m), 2.6, 0.17)
    shrug1 = cues["s2a"]["end"] + 0.1
    shrug2 = cues["s2b"]["end"] + 0.1
    S.note("marimba", shrug1, nm("E5"), 0.3, 0.3)
    S.note("marimba", shrug1 + 0.25, nm("C#5"), 0.4, 0.27)
    S.note("marimba", shrug2, nm("D5"), 0.3, 0.3)
    S.note("marimba", shrug2 + 0.25, nm("B4"), 0.4, 0.27)
    status = cues["s2c"]["start"] + 1.62                    # "...the status."
    for m in voicing("Gmaj7", 55):
        S.note("vibes", cues["s2c"]["start"], m, status - cues["s2c"]["start"], 0.2)
    for m in voicing("Dadd9", 57):
        S.note("vibes", status, m, 2.0, 0.34)
    S.note("bass", status, nm("D2"), 1.6, 0.45, slide=0.2)
    S.note("marimba", status, nm("D5"), 0.5, 0.35)
    S.note("marimba", cues["s2c"]["end"] + 0.08, nm("A4"), 0.3, 0.3)
    S.note("marimba", cues["s2c"]["end"] + 0.33, nm("D5"), 0.5, 0.33)

    # ── desc (32.5-65): 102.9 BPM so the callouts fall on the beat ──
    beat = ev["s3.callout1"] - ev["s3.callout0"]
    dsc = Sec(S, ev["s3.callout0"] - 8 * beat, 60 / beat)
    DESC = "D | D/F# | G | A | Bm | G | Em7 | A7 | D | Bm | G | A7sus4 A7 | D"
    dsc.mel("vibes", "r:2 A4:1 D5:1 | F#5:3 E5:1 | D5:2 B4:2 | C#5:2 E5:2 | "
            "F#5:1.5 E5:0.5 D5:2 | B4:3 r:1 | G5:1 F#5:1 E5:1 D5:1 | C#5:2 A4:2", 1, vel=0.42)
    dsc.mel("mbox", "D6:0.5 A5:0.5 F#5:0.5 A5:0.5 D6:1 E6:1 | F#6:1 D6:1 B5:2 | "
            "G5:0.5 B5:0.5 D6:1 B5:1 G5:1 | A5:2 C#6:1 E6:1 | F#6:3 D6:1", 9, vel=0.45)
    arp8(dsc, "marimba", "G | A", 3, 0.3, 55)
    arp8(dsc, "marimba", "D | Bm | G | A7sus4 A7", 9, 0.22, 62)
    for bi, cell in enumerate(bars(DESC)):
        for sym, b0, nb in cell:
            dsc.bass(sym, bi + 1, b0, min(2, nb), 0.42 if bi else 0.3)
            if 4 <= bi <= 11 and nb >= 4:
                dsc.bass(sym, bi + 1, b0 + 2, 2, 0.32, midi=alt_bass(sym))
    for bi in range(4, 8):
        for sym, b0, nb in bars(DESC)[bi]:
            for k in (1, 3):
                for j, m in enumerate(voicing(sym, 55)[:3]):
                    S.note("pizzmid", dsc.T(bi + 1, k) + j * 0.012, m, 0.3, 0.32)
    dsc.chord("vibes", "D", 13, 0, 3, 0.3, 57)
    pads(dsc, "D", 13, 0.18, overlap=0.5)

    # ── offline (65-89.75): theme A, pizzicato and brushes ──
    off = Sec(S, ev["s4.turn0"], 92)
    S.note("pizz", off.T(0, 3), nm("A4"), 0.3, 0.38)
    S.note("pizz", off.T(0, 3.5), nm("C#5"), 0.3, 0.42)
    off.mel("pizz", THEME_A_MEL, 1, vel=0.6)
    accompany(off, THEME_A, "oompah", vel=0.55, next_after="D")
    brushes(off, 1, 8, vel=0.9, tw=0.0)
    brushes(off, 1, 3, vel=0.9, tw=0.18, swirl=False, taps=False)
    brushes(off, 7, 8, vel=0.9, tw=0.18, swirl=False, taps=False)
    S.note("bass", off.T(9, 0), nm("A2"), 1.2, 0.35)
    off.chord("vibes", "A7sus4", 9, 0, 2.2, 0.22, 57)

    # ── preflight (89.75-129.25) ──
    drop = drop_window(cut)
    preflight_block(S, ev["s5.warning"], 12, drop, drop[1] + 0.05)
    S.note("vibes", ev["s5.lid"] + 0.3, nm("A4"), 0.8, 0.2)
    S.note("vibes", ev["s5.lid"] + 0.6, nm("F#4"), 1.4, 0.2)

    # ── canards (129.25-149.75): marimba takes the tune ──
    can = Sec(S, ev["s5.turn"] + 1.1, 92)
    CAN = "D | A/C# | Bm | G | Em7 | A7 | D | D"
    can.mel("marimba", mel_bars(THEME_A_MEL, 0, 4), 1, vel=0.5)
    can.mel("marimba", mel_bars(THEME_A_MEL, 6, 8), 5, vel=0.5)
    can.mel("marimba", "F#5:1 D5:0.5 E5:0.5 F#5:1 A5:1 | D5:2 r:2", 7, vel=0.48)
    can.mel("pizz", "r:4 | r:4 | r:4 | r:2 B4:0.5 C#5:0.5 D5:1", 1, vel=0.4)
    accompany(can, prog_bars(CAN, 0, 7), "half", vel=0.5, next_after="D")
    brushes(can, 1, 7, vel=0.8, tw=0.1)
    can.chord("vibes", "Dadd9", 8, 0, 2.6, 0.26, 57)
    can.bass("D", 8, 0, 2.5, 0.4)

    # ── passport (149.75-164.25): pads under the evidence beats ──
    pas = Sec(S, cues["s7a"]["start"] - 0.25, 92)
    PAS = "G | D/F# | Em7 | A7sus4 A7 | Gmaj7"
    pads(pas, PAS, 1, 0.5, overlap=0.6)
    pas.mel("vibes", "B4:2 D5:2 | A4:3 F#4:1 | G4:2 B4:2 | A4:2 C#5:2 | B4:4", 1, vel=0.4)
    arp8(pas, "pizzmid", prog_bars(PAS, 0, 3), 1, 0.3, 55, pattern=(0, 2, 1, 2, 0, 2, 1, 2))
    accompany(pas, PAS, "roots", vel=0.45)
    for m in voicing("Gmaj7", 50):
        S.note("pad", pas.T(6), m, 1.0, 0.38, human=False, release=2.0)

    # ── abnormal (164.25-190.5): B minor, a steady soft pulse ──
    abn = Sec(S, ev["s8.turn0"] - 0.1, 84)
    ABN = "Bm | Bm/A | Gmaj7 | F#7sus4 F#7 | Bm | Em | G A | D"
    for m in voicing("Bm", 50):
        S.note("pad", ev["s7.turn"] + 0.4, m, abn.t0 - ev["s7.turn"], 0.25, human=False, attack=1.5)
    pads(abn, ABN, 1, 0.3, overlap=0.4)
    abn.mel("vibes", "r:2 F#5:2 | E5:2 D5:2 | B4:3 r:1 | B4:2 A#4:2 | r:2 D5:1 F#5:1 | "
            "G5:2 E5:2 | D5:2 C#5:2 | F#5:4", 1, vel=0.4)
    for bi, cell in enumerate(bars(ABN)):
        bar = bi + 1
        if bar == 6:                               # "Silence points to..." -- the pulse rests
            abn.bass(cell[0][0], bar, 0, 3.5, 0.32)
            continue
        if bar == 8:
            abn.bass("D", bar, 0, 3.5, 0.45, slide=0.25)
            abn.chord("vibes", "D", bar, 0, 4, 0.3, 57)
            continue
        for sym, b0, nb in cell:
            for k in range(int(nb)):
                m = bass_of(sym)
                abn.bass(sym, bar, b0 + k, 0.55, 0.36 if k == 0 else 0.3, midi=m)
                fifth = voicing(sym, 62)[-1]
                S.note("marimba", abn.T(bar, b0 + k + 0.5), fifth, 0.2, 0.18, damp=True)
    S.note("mbox", abn.T(8, 2), nm("A5"), 1.0, 0.3)
    S.note("mbox", abn.T(8, 3), nm("D6"), 1.5, 0.3)

    # ── limits (190.5-218): felt piano, slower and sparer ──
    S.note("piano", ev["s8.turn"] + 0.9, nm("F#2"), 2.8, 0.3)
    S.note("piano", ev["s8.turn"] + 0.9, nm("D3"), 2.8, 0.28)
    S.note("piano", ev["s8.turn"] + 1.2, nm("A4"), 2.5, 0.3)
    lim = Sec(S, ev["s9.turn0"] + 0.15, 64)
    LIM = "Gmaj9 | D/F# | Em7 | Bm7 A | Gmaj7 | Asus4 D/F# | D/F#"
    lim.mel("piano", "r:1 B4:1 F#5:2 | E5:1.5 D5:0.5 A4:2 | G4:1 B4:1 D5:1 E5:1 | "
            "F#5:2 E5:1 C#5:1 | D5:3 B4:1 | E5:1.5 D5:0.5 F#5:2 | r:1 A5:3", 1, vel=0.5, legato=1.3)
    for bi, cell in enumerate(bars(LIM)):
        for sym, b0, nb in cell:
            r = bass_of(sym, 38)
            top = voicing(sym, 55)
            if nb >= 4:
                seq = [r, r + 7, top[1] if len(top) > 1 else r + 16, r + 7]
            else:
                seq = [r, top[1] if len(top) > 1 else r + 12]
            if bi == 6:
                seq = [r, r + 8]
            for k, m in enumerate(seq):
                S.note("piano", lim.T(bi + 1, b0 + k), m, (nb - k) * lim.b + 0.3, 0.3 if k else 0.36)
    pads(lim, prog_bars(LIM, 0, 6), 1, 0.16, lo=50, overlap=0.8, cutoff=700)

    # ── gates (218-226.75): pads, music box answer to the beads ──
    g0 = ev["s9.turn"] + 0.55
    gch = [("Dadd9", g0, 2.6), ("F#m7", g0 + 2.6, 2.0), ("Bm7", g0 + 4.6, 2.0), ("Em9", g0 + 6.6, 2.6)]
    for sym, t, d in gch:
        for m in voicing(sym, 50):
            S.note("pad", t, m, d + 0.4, 0.42, human=False)
        S.note("marimba", t, voicing(sym, 50)[0], 0.5, 0.28)
    t_mb = ev["s10.bead7"] + 0.5
    for dt, m, v in [(0, "F#6", 0.35), (0.65, "E6", 0.32), (1.3, "D6", 0.34), (2.6, "C#6", 0.3), (3.3, "B5", 0.32)]:
        S.note("mbox", t_mb + dt, nm(m), 1.0, v)

    # ── end (226.75-239): theme recap, final cadence lands on the lamp-off ──
    eb = 60 / 84
    end = Sec(S, ev["s10.lampOff"] - 8 * eb, 84)
    END = "Gmaj7 | A7sus4 A7"
    end.mel("vibes", "B5:1 A5:0.5 F#5:0.5 D5:2 | A5:1 G5:0.5 E5:0.5 C#5:1 E5:1", 1, vel=0.4, transpose=-12)
    S.note("pizz", end.T(0, 3), nm("A4"), 0.3, 0.35)
    pads(end, END, 1, 0.42, overlap=0.4)
    accompany(end, END, "half", vel=0.45, next_after="D")
    land = end.T(3)
    for m in [nm("D2")]:
        S.note("bass", land, m, 3.5, 0.5, slide=0.25)
    for m in voicing("Dadd9", 50):
        S.note("pad", land, m, 3.0, 0.45, human=False, release=2.2)
    for m in [nm("D3"), nm("A3"), nm("F#4")]:
        S.note("piano", land, m, 3.5, 0.36, human=False)
    end.chord("vibes", "D", 3, 0, 4, 0.36, 57)
    S.note("mbox", land, nm("A5"), 1.0, 0.36, human=False)
    S.note("mbox", land + 0.36, nm("D6"), 1.5, 0.38)
    # an "amen" after "Run the review."
    amen = cues["s10c"]["end"] + 0.5
    for m in voicing("G", 50):
        S.note("pad", amen, m, 1.6, 0.32, human=False, attack=0.8)
    for m in voicing("Dadd9", 50):
        S.note("pad", amen + 1.7, m, 1.8, 0.32, human=False, attack=0.9, release=2.0)
    S.note("piano", amen + 1.7, nm("D3"), 2.0, 0.3)
    S.note("piano", amen + 1.75, nm("A4"), 2.0, 0.28)

    # ── credits (239-248.8): music box reprise, fading out ──
    cr = Sec(S, ev["s10.endHold"] + 0.5, 72)
    cr.mel("mbox", "A5:1 F#5:0.5 A5:0.5 D6:2 | E5:1 A4:1 D5:2", 1, vel=0.36, legato=1.0)
    for m in voicing("Dadd9", 50):
        S.note("pad", cr.t0 - 0.4, m, 5.0, 0.26, human=False, attack=1.5, release=2.0)
    S.note("bass", cr.t0, nm("D2"), 2.5, 0.3)
    return S


# ════════════════════════════════════════════════════════════════════════════
# Score: preflight60 (vertical social cut)
# ════════════════════════════════════════════════════════════════════════════

def score_pre60(cut):
    S = Score("preflight60")
    ev = cut["events"]
    cues = {c["id"]: c for c in cut["cues"]}
    vc = Sec(S, ev["v.lampOn"] + 0.3, 84)
    vc.mel("mbox", "A5:1 F#5:0.5 A5:0.5 D6:2", 1, vel=0.5)
    vc.chord("vibes", "Dadd9", 1, 0, 3.5, 0.3, 57, roll=0.03)
    vc.bass("D", 1, 0, 3, 0.3)

    leads = [ev[f"v.lead{i}"] for i in range(9)]
    for t, m in zip(leads, ["D4", "E4", "F#4", "G4", "A4", "B4", "C#5", "D5", "E5"]):
        S.note("marimba", t, nm(m), 0.3, 0.36)
    for m in voicing("Gmaj7", 57):
        S.note("vibes", leads[0], m, 1.0, 0.22)
    for m in ("A3", "B3", "E4"):
        S.note("vibes", leads[8], nm(m), 3.0, 0.2)
    for m in ("G3", "B3", "E4"):
        S.note("vibes", cues["s2b"]["start"] - 0.2, nm(m), 2.6, 0.17)
    shrug1 = cues["s2a"]["end"] + 0.1
    shrug2 = cues["s2b"]["end"] + 0.1
    S.note("marimba", shrug1, nm("E5"), 0.3, 0.3)
    S.note("marimba", shrug1 + 0.25, nm("C#5"), 0.4, 0.27)
    S.note("marimba", shrug2, nm("D5"), 0.3, 0.3)
    S.note("marimba", shrug2 + 0.25, nm("B4"), 0.4, 0.27)
    status = cues["s2c"]["start"] + 1.62
    for m in voicing("Gmaj7", 55):
        S.note("vibes", cues["s2c"]["start"], m, status - cues["s2c"]["start"], 0.2)
    for m in voicing("Dadd9", 57):
        S.note("vibes", status, m, 1.6, 0.34)
    S.note("bass", status, nm("D2"), 1.2, 0.45, slide=0.2)
    S.note("marimba", status, nm("D5"), 0.5, 0.35)
    S.note("marimba", cues["s2c"]["end"] + 0.08, nm("A4"), 0.3, 0.3)

    drop = drop_window(cut)
    preflight_block(S, ev["v.warning"], 11, drop, drop[1] + 0.05)

    # vend: a short plagal-to-tonic landing around "Run the review."
    e0 = ev["v.end"] + 0.4
    for sym, t, d in [("Gmaj7", e0, 1.4), ("A7sus4", e0 + 1.4, 1.4)]:
        for m in voicing(sym, 50):
            S.note("pad", t, m, d + 0.3, 0.36, human=False, attack=0.5)
        S.note("bass", t, bass_of(sym), d, 0.4)
    land = e0 + 2.8
    for m in voicing("Dadd9", 50):
        S.note("pad", land, m, 3.5, 0.42, human=False, release=2.2)
    S.note("bass", land, nm("D2"), 3.0, 0.48, slide=0.25)
    for m in voicing("D", 57):
        S.note("vibes", land, m, 3.5, 0.34)
    for m in [nm("D3"), nm("A3"), nm("F#4")]:
        S.note("piano", land, m, 3.5, 0.34, human=False)
    S.note("mbox", land, nm("A5"), 1.0, 0.34, human=False)
    S.note("mbox", land + 0.36, nm("D6"), 1.5, 0.36)
    S.note("mbox", land + 3.2, nm("F#5"), 1.2, 0.22)
    S.note("mbox", land + 3.9, nm("D5"), 2.0, 0.2)
    return S


# ════════════════════════════════════════════════════════════════════════════
# Music render
# ════════════════════════════════════════════════════════════════════════════

def render_music(S, n, drop, fade_end):
    dry = np.zeros((n, 2))
    send = np.zeros((n, 2))
    stats = {}
    for e in sorted(S.ev, key=lambda e: e["t"]):
        fn, gdb, snd, dpan = INST[e["inst"]]
        f = mtof(e["midi"]) if e["midi"] else 0.0
        r = rng_for(S.name, e["inst"], round(e["t"], 4), e["midi"], "syn")
        x = fn(f, e["dur"], e["vel"], r, **e["kw"])
        pan = e["pan"]
        if pan is None:
            pan = dpan
            if e["inst"] in ("piano", "marimba", "vibes") and e["midi"]:
                pan = dpan + float(np.clip((e["midi"] - 64) / 60, -0.25, 0.25))
        g = undb(gdb)
        add(dry, x, e["t"], pan, g)
        add(send, x, e["t"], pan, g * snd)
        stats[e["inst"]] = stats.get(e["inst"], 0) + 1
    ir = make_ir(1.45, 2.2, 1234)
    music = dry + 0.55 * convolve_st(send, ir)
    music = hp(music, 30)
    # the comic beat: music out from just before "It refuses." to after "Good."
    t = tvec(n)
    gate = np.ones(n)
    a, b = drop
    ramp = 0.12
    gate[(t >= a) & (t <= b)] = 0.0
    m1 = (t > a - ramp) & (t < a)
    gate[m1] = np.cos((t[m1] - (a - ramp)) / ramp * np.pi / 2) ** 2
    m2 = (t > b) & (t < b + ramp)
    gate[m2] = np.sin((t[m2] - b) / ramp * np.pi / 2) ** 2
    fs, fe = fade_end
    m3 = (t > fs) & (t < fe)
    gate[m3] *= np.cos((t[m3] - fs) / (fe - fs) * np.pi / 2) ** 2
    gate[t >= fe] = 0.0
    return music * gate[:, None], stats


# ════════════════════════════════════════════════════════════════════════════
# Sound design (one function per sfx kind)
# ════════════════════════════════════════════════════════════════════════════

def click_core(rng, modes, decays, amps, noise_amp=1.0, noise_tau=0.0012, hpf=1500, length=0.08, j=1.0):
    n = ns(length)
    t = tvec(n)
    x = hp(noise(rng, n), hpf) * np.exp(-t / noise_tau) * noise_amp
    for f, d, a in zip(modes, decays, amps):
        x += a * np.sin(2 * np.pi * f * j * t + rng.uniform(0, 6.28)) * np.exp(-t / d)
    return fade(x, 0.0001, 0.01)


def place(dst, x, t):
    i = ns(t) if t > 0 else 0
    if i >= len(dst):
        return
    k = min(len(x), len(dst) - i)
    dst[i:i + k] += x[:k]


def sfx_lamp(rng, on=False, **_):
    out = np.zeros(ns(0.16))
    c1 = click_core(rng, [1850, 3150, 4700, 900], [0.012, 0.008, 0.005, 0.02], [0.5, 0.35, 0.2, 0.3],
                    noise_tau=0.0011, length=0.08)
    c2 = click_core(rng, [2050, 3400, 1000], [0.009, 0.006, 0.015], [0.4, 0.25, 0.25],
                    noise_amp=0.6, noise_tau=0.0008, length=0.06)
    place(out, c1, 0)
    place(out, 0.55 * c2, 0.028)
    tt = tvec(ns(0.05))
    place(out, 0.25 * np.sin(2 * np.pi * 140 * tt) * np.exp(-tt / 0.012), 0)
    return out


def lamp_hum(n):
    t = tvec(n)
    env = np.sin(np.pi * np.clip(t / (n / SR), 0, 1)) ** 2
    x = (np.sin(2 * np.pi * 120 * t) + 0.5 * np.sin(2 * np.pi * 240 * t + 1)
         + 0.25 * np.sin(2 * np.pi * 360 * t + 2)) * env
    return x / np.abs(x).max()


def sfx_rings(rng, **_):
    out = np.zeros(ns(0.25))
    for dt, j, a in [(0, 1.0, 1.0), (0.007, 1.045, 0.8), (0.016, 0.97, 0.35)]:
        c = click_core(rng, [2350, 3420, 4980, 6200, 1250], [0.035, 0.025, 0.018, 0.012, 0.02],
                       [0.5, 0.45, 0.35, 0.2, 0.3], noise_amp=1.2, noise_tau=0.0007, hpf=2500,
                       length=0.2, j=j)
        place(out, a * c, dt)
    tt = tvec(ns(0.2))
    place(out, 0.06 * np.sin(2 * np.pi * 2930 * tt) * np.exp(-tt / 0.06), 0.002)
    return out


def crinkle(rng, n, rate, lo=2000, hi=7000):
    imp = np.zeros(n)
    k = rng.poisson(rate * n / SR)
    idx = rng.integers(0, n, k)
    imp[idx] = rng.uniform(-1, 1, k) * rng.uniform(0.2, 1.0, k) ** 2
    return bp(imp, lo, hi)


def bump(n, peak=0.4, a=1.6, b=2.4):
    x = np.linspace(0, 1, n)
    e = (x / peak) ** a * np.exp(a * (1 - x / peak)) if peak > 0 else np.ones(n)
    return e / e.max() * (1 - x) ** (b * 0.25)


def sfx_page(rng, soft=0, L=None, sweep=(700, 3600, 1700), crink=140, flap=True, **_):
    L = L or (0.42 if soft else 0.62)
    n = ns(L)
    t = tvec(n)
    x = np.linspace(0, 1, n)
    fc = np.where(x < 0.45, sweep[0] + (sweep[1] - sweep[0]) * (x / 0.45) ** 0.8,
                  sweep[1] + (sweep[2] - sweep[1]) * ((x - 0.45) / 0.55))
    env = bump(n, 0.42)
    w = noise(rng, n)
    swish = tv_bandpass(w, fc, q=0.7) * env
    air = lp(noise(rng, n), 450) * env * 0.6
    cr = crinkle(rng, n, crink) * (env ** 0.7) * 2.2
    y = swish + air + cr
    if flap:
        k = ns(0.035)
        f = bp(noise(rng, k), 250, 1100) * edecay(k, 0.009) * 1.2
        place(y, f, L * 0.86)
    y = fade(y, 0.01, 0.06)
    return y * (0.6 if soft else 1.0)


def sfx_unfold(rng, **_):
    y = sfx_page(rng, L=0.95, sweep=(500, 2600, 1200), crink=210)
    pop = click_core(rng, [1500, 2600, 700], [0.008, 0.005, 0.012], [0.5, 0.3, 0.4],
                     noise_amp=1.2, noise_tau=0.0009, hpf=1200, length=0.05)
    place(y, 0.9 * pop, 0.55)
    tt = tvec(ns(0.04))
    place(y, 0.4 * np.sin(2 * np.pi * 180 * tt) * np.exp(-tt / 0.01), 0.55)
    return y


def sfx_paper(rng, **_):
    y = sfx_page(rng, L=0.4, sweep=(1200, 4000, 2500), crink=180, flap=False)
    pop = click_core(rng, [1800, 3100], [0.006, 0.004], [0.4, 0.25], noise_amp=1.0,
                     noise_tau=0.0008, hpf=1500, length=0.04)
    place(y, 0.7 * pop, 0.09)
    return y


def sfx_slip(rng, **_):
    n = ns(0.9)
    t = tvec(n)
    x = np.linspace(0, 1, n)
    fc = 1200 + 4000 * x ** 1.3
    w = tv_bandpass(noise(rng, n), fc, q=1.1)
    rate = 14 + 12 * x
    flutter = 1 - 0.55 * (0.5 + 0.5 * np.sin(2 * np.pi * np.cumsum(rate) / SR + rng.uniform(0, 6)))
    env = np.minimum(1, x / 0.15) * np.minimum(1, (1 - x) / 0.12) * (0.6 + 0.4 * x)
    y = w * flutter * env
    tick = np.zeros(n)
    tick[(np.arange(0, n, ns(1 / 70)))] = 1
    y += 0.25 * bp(tick, 1500, 3000) * env
    y += 0.5 * crinkle(rng, n, 60, 2500, 8000) * env
    return fade(y, 0.01, 0.05)


def sfx_card(rng, **_):
    out = np.zeros(ns(0.3))
    tap = click_core(rng, [900, 1700, 2900], [0.01, 0.007, 0.005], [0.4, 0.3, 0.2], noise_amp=1.0,
                     noise_tau=0.0018, hpf=800, length=0.06)
    tt = tvec(ns(0.05))
    place(out, tap + 0, 0)
    place(out, 0.4 * np.sin(2 * np.pi * 220 * tt) * np.exp(-tt / 0.015), 0)
    k = ns(0.17)
    sl = bp(noise(rng, k), 1500, 4500) * bump(k, 0.2) * 0.35
    place(out, sl, 0.02)
    return fade(out, 0.0, 0.03)


def sfx_stamp(rng, small=False, **_):
    s = 1.25 if small else 1.0
    n = ns(0.35)
    t = tvec(n)
    f = (70 + 40 * np.exp(-t / 0.02)) * s
    th = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / (0.07 / s)) * (1 - np.exp(-t / 0.001))
    slap = lp(noise(rng, n), 2500) * np.exp(-t / 0.012) * 0.5
    sq = lp(noise(rng, n), 600) * np.exp(-t / 0.04) * 0.35
    tack = 0.15 * np.sin(2 * np.pi * 1100 * s * t) * np.exp(-t / 0.015)
    y = th + slap + sq + tack
    return fade(y, 0.0, 0.05) * (0.65 if small else 1.0)


def sfx_thunk(rng, soft=0, **_):
    n = ns(0.25)
    t = tvec(n)
    f = 115 + 40 * np.exp(-t / 0.015)
    th = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.04) * (1 - np.exp(-t / 0.0015))
    nz = lp(noise(rng, n), 900) * np.exp(-t / 0.025) * 0.6
    sq = bp(noise(rng, n), 250, 1100) * (t / 0.02) * np.exp(1 - t / 0.02) * 0.25
    y = th + nz + sq
    if soft:
        y = lp(y, 1500) * np.exp(-t / 0.08)
    return fade(y, 0.0, 0.04) * (0.6 if soft else 1.0)


def sfx_squish(rng, soft=0, **_):
    L = 0.3 if soft else 0.42
    n = ns(L)
    t = tvec(n)
    x = np.linspace(0, 1, n)
    fc = 380 + 170 * np.sin(2 * np.pi * 6.5 * t + rng.uniform(0, 3)) * (1 - x) + 120 * x
    y = tv_bandpass(noise(rng, n), fc, q=2.2)
    env = np.minimum(1, t / 0.04) * (1 - x) ** 1.4
    y *= env
    wob = np.sin(2 * np.pi * np.cumsum(105 + 25 * np.sin(2 * np.pi * 9 * t)) / SR) * np.exp(-t / 0.08) * 0.25
    y += wob
    for _ in range(4):
        k = ns(0.004)
        c = lp(noise(rng, k), 3000) * edecay(k, 0.001) * 0.35
        place(y, c, rng.uniform(0.03, L * 0.7))
    return fade(y, 0.004, 0.04) * (0.6 if soft else 1.0)


def graphite(rng, n, lo, hi, grain_rate, grain_mix):
    w = bp(noise(rng, n), lo, hi)
    imp = np.zeros(n)
    k = rng.poisson(grain_rate * n / SR)
    imp[rng.integers(0, n, k)] = rng.uniform(0.3, 1.0, k)
    g = uniform_filter1d(imp, ns(0.0004)) * 40
    return w * ((1 - grain_mix) + grain_mix * g)


def sfx_tick(rng, **_):
    n = ns(0.08)
    t = tvec(n)
    y = graphite(rng, n, 2000, 6000, 1500, 0.7)
    y *= np.minimum(1, t / 0.004) * np.exp(-t / 0.022)
    tt = tvec(n)
    y += 0.08 * np.sin(2 * np.pi * 900 * tt) * np.exp(-tt / 0.01)
    return fade(y, 0.001, 0.015)


def sfx_pencil(rng, L=0.2, **_):
    n = ns(L)
    y = graphite(rng, n, 1800, 5200, 1100, 0.7)
    return fade(y * bump(n, 0.3), 0.004, 0.03)


def sfx_pen(rng, **_):
    n = ns(0.25)
    t = tvec(n)
    y = graphite(rng, n, 1500, 4200, 600, 0.25)
    y *= np.sin(np.pi * np.linspace(0, 1, n)) ** 0.8
    return fade(y, 0.006, 0.04) * 0.8


def sfx_scribble(rng, **_):
    n = ns(0.7)
    t = tvec(n)
    w = noise(rng, n)
    fc = 3000 + 900 * np.sin(2 * np.pi * 3.2 * t)
    y = tv_bandpass(w, fc, q=1.2)
    imp = np.zeros(n)
    k = rng.poisson(1100 * n / SR)
    imp[rng.integers(0, n, k)] = rng.uniform(0.3, 1.0, k)
    y *= 0.4 + 0.6 * uniform_filter1d(imp, ns(0.0004)) * 40
    y *= 0.2 + 0.8 * np.abs(np.sin(2 * np.pi * 3.2 * t + 0.4)) ** 1.5
    y *= np.minimum(1, t / 0.03) * np.minimum(1, (0.7 - t) / 0.08)
    return fade(y, 0.004, 0.03)


def keystroke(rng, j, a):
    out = np.zeros(ns(0.09))
    c = click_core(rng, [1100, 2300], [0.012, 0.007], [0.35, 0.25], noise_amp=0.6,
                   noise_tau=0.0008, hpf=1800, length=0.04, j=j)
    tt = tvec(ns(0.03))
    c[:len(tt)] += 0.3 * np.sin(2 * np.pi * 260 * j * tt) * np.exp(-tt / 0.008)
    place(out, c, 0)
    up = click_core(rng, [1500, 2800], [0.006, 0.004], [0.2, 0.15], noise_amp=0.25,
                    noise_tau=0.0006, hpf=2000, length=0.03, j=j)
    place(out, 0.3 * up, rng.uniform(0.045, 0.07))
    return out * a


def sfx_keys(rng, n=10, dur=0.5, **_):
    out = np.zeros(ns(dur + 0.15))
    step = dur / n
    for i in range(int(n)):
        t = (i + 0.5) * step + rng.uniform(-0.3, 0.3) * step
        place(out, keystroke(rng, rng.uniform(0.9, 1.12), undb(rng.uniform(-4, 1))), max(0, t))
    return out


def sfx_click(rng, **_):
    out = np.zeros(ns(0.08))
    c1 = click_core(rng, [1400, 2600], [0.01, 0.006], [0.4, 0.25], noise_amp=0.7,
                    noise_tau=0.0006, hpf=1200, length=0.05)
    c2 = click_core(rng, [1290, 2400], [0.008, 0.005], [0.3, 0.2], noise_amp=0.4,
                    noise_tau=0.0005, hpf=1200, length=0.05)
    place(out, c1, 0)
    place(out, 0.5 * c2, 0.014)
    tt = tvec(ns(0.04))
    place(out, 0.15 * np.sin(2 * np.pi * 300 * tt) * np.exp(-tt / 0.01), 0)
    return lp(out, 6000)


def sfx_toggle(rng, **_):
    out = np.zeros(ns(0.2))
    c1 = click_core(rng, [1700, 3000], [0.008, 0.005], [0.3, 0.2], noise_amp=0.5,
                    noise_tau=0.0006, length=0.04)
    place(out, 0.4 * c1, 0)
    c2 = click_core(rng, [1100, 2300, 3600], [0.02, 0.012, 0.008], [0.5, 0.35, 0.2],
                    noise_amp=1.0, noise_tau=0.0010, length=0.12)
    tt = tvec(ns(0.15))
    spring = 0.18 * np.sin(2 * np.pi * np.cumsum(880 + 15 * np.sin(2 * np.pi * 35 * tt)) / SR) * np.exp(-tt / 0.06)
    thump = 0.35 * np.sin(2 * np.pi * 190 * tt) * np.exp(-tt / 0.015)
    place(out, c2, 0.016)
    place(out, spring + thump, 0.016)
    return fade(out, 0, 0.02)


def sfx_beep(rng, **_):
    n = ns(0.12)
    t = tvec(n)
    y = np.sin(2 * np.pi * 2200 * t) + 0.06 * np.sin(2 * np.pi * 4400 * t)
    return fade(y, 0.015, 0.03)


def sfx_buzz(rng, **_):
    n = ns(0.32)
    t = tvec(n)
    f0 = 310
    y = sum((1 / k) * np.sin(2 * np.pi * f0 * k * t + 0.3 * k) for k in (1, 3, 5, 7, 9))
    y += 0.15 * np.sin(2 * np.pi * f0 * 2 * t)
    y *= 1 + 0.12 * np.sin(2 * np.pi * 50 * t)
    y = lp(y, 1300, 2)
    return fade(y, 0.025, 0.07)


def sfx_whir(rng, n=1, **_):
    moves = []
    t = 0.0
    for i in range(int(n)):
        d = rng.uniform(0.17, 0.3)
        moves.append((t, d))
        t += d + rng.uniform(0.06, 0.12)
    out = np.zeros(ns(t + 0.1))
    for t0, d in moves:
        k = ns(d)
        tt = tvec(k)
        x = np.linspace(0, 1, k)
        s = np.sin(np.pi * x) ** 0.6
        f0 = rng.uniform(560, 820) * (0.75 + 0.25 * s)
        ph = 2 * np.pi * np.cumsum(f0) / SR + 0.35 * np.sin(2 * np.pi * 37 * tt)
        y = sum(a * np.sin(h * ph) for h, a in ((1, 1.0), (2, 0.45), (3, 0.25), (4, 0.12), (5, 0.06)))
        y += 0.12 * bp(noise(rng, k), 900, 2500) * s
        env = s ** 0.3 * np.minimum(1, tt / 0.025) * np.minimum(1, (d - tt) / 0.045)
        place(out, lp(y * env, 3200), t0)
    return fade(out, 0.002, 0.02)


def sfx_felt(rng, dur=1.0, **_):
    n = ns(dur)
    t = tvec(n)
    w = noise(rng, n)
    y = lp(w, 1300) + 0.25 * bp(w, 2000, 3500)
    gr = lp(noise(rng, n), 30)
    gr = gr / (np.abs(gr).max() + 1e-9)
    y *= 0.6 + 0.4 * gr
    y *= np.minimum(1, t / 0.12) * np.minimum(1, (dur - t) / 0.2) * (0.8 + 0.2 * np.sin(np.pi * t / dur))
    return fade(y, 0.01, 0.05)


def sfx_clink(rng, **_):
    out = np.zeros(ns(0.45))
    for dt, a, j in [(0, 1.0, 1.0), (0.075, 0.35, 1.03)]:
        n = ns(0.35)
        t = tvec(n)
        y = sum(am * np.sin(2 * np.pi * f * j * t + rng.uniform(0, 6)) * np.exp(-t / d)
                for f, d, am in zip([2150, 3260, 4630, 5960, 7890], [0.22, 0.15, 0.1, 0.07, 0.04],
                                    [1, 0.6, 0.45, 0.3, 0.2]))
        y += lp(noise(rng, n), 1200) * np.exp(-t / 0.008) * 0.6
        y += 0.15 * np.sin(2 * np.pi * 1250 * t) * np.exp(-t / 0.3)
        place(out, a * y * (1 - np.exp(-t / 0.0004)), dt)
    return fade(out, 0, 0.05)


def sfx_lid(rng, **_):
    out = np.zeros(ns(0.3))
    k = ns(0.2)
    t = tvec(k)
    puff = bp(noise(rng, k), 200, 700) * bump(k, 0.25) * 0.3
    place(out, puff, 0)
    clap = lp(noise(rng, k), 900) * np.exp(-t / 0.035) * (1 - np.exp(-t / 0.002))
    clap += 0.5 * np.sin(2 * np.pi * 95 * t) * np.exp(-t / 0.03)
    place(out, clap, 0.04)
    latch = click_core(rng, [2000], [0.006], [0.2], noise_amp=0.3, noise_tau=0.0005, length=0.03)
    place(out, 0.4 * latch, 0.062)
    return fade(out, 0.004, 0.03)


def sfx_chime(rng, pitches=("A5", "D6"), soft=0, **_):
    out = np.zeros(ns(1.2))
    for i, p in enumerate(pitches):
        x = syn_marimba(mtof(nm(p)), 0.8, 0.7 - 0.08 * i, rng)
        place(out, x, 0.13 * i)
    return out * (0.6 if soft else 1.0)


def sfx_plink(rng, midi=86, **_):
    return syn_mbox(mtof(midi), 1.0, 0.7, rng)


def sfx_plinks(rng, midis=(81, 83, 86), **_):
    out = np.zeros(ns(0.25 * len(midis) + 1.6))
    for i, m in enumerate(midis):
        place(out, syn_mbox(mtof(m), 1.0, 0.65 + 0.05 * i, rng), 0.25 * i)
    return out


SFX = {
    "lamp": sfx_lamp, "rings": sfx_rings, "page": sfx_page, "stamp": sfx_stamp,
    "stampSmall": lambda rng, **k: sfx_stamp(rng, small=True), "thunk": sfx_thunk,
    "squish": sfx_squish, "tick": sfx_tick, "pencil": sfx_pencil, "pen": sfx_pen,
    "scribble": sfx_scribble, "keys": sfx_keys, "click": sfx_click, "toggle": sfx_toggle,
    "beep": sfx_beep, "buzz": sfx_buzz, "whir": sfx_whir, "felt": sfx_felt, "card": sfx_card,
    "unfold": sfx_unfold, "paper": sfx_paper, "slip": sfx_slip, "clink": sfx_clink,
    "lid": sfx_lid, "chime": sfx_chime, "plink": sfx_plink, "plinks": sfx_plinks,
}

# Max momentary loudness (LUFS, before the master trim) for each kind, and a
# default pan. Voice sits at about -16.5, so these all sit well below it.
SFX_TARGET = {
    "lamp": -31, "rings": -28, "page": -29, "stamp": -25, "stampSmall": -29, "thunk": -28,
    "squish": -30, "tick": -33, "pencil": -32, "pen": -33, "scribble": -31, "keys": -32,
    "click": -32, "toggle": -29, "beep": -33, "buzz": -32, "whir": -32, "felt": -34,
    "card": -30, "unfold": -28, "paper": -30, "slip": -30, "clink": -29, "lid": -29,
    "chime": -30, "plink": -31, "plinks": -30,
}
SFX_PAN = {"lamp": 0.25, "keys": -0.15, "whir": 0.1, "beep": 0.15, "buzz": 0.15, "clink": -0.15,
           "chime": 0.12, "plink": 0.1, "plinks": 0.1, "lid": -0.1, "toggle": 0.12}
SOFT_DROP = 5.0   # LU quieter for soft=1
SFX_OFFSET = 3.0  # global sfx trim
SFX_PEAK_CAP = -15.0  # dBFS per event before the master trim


def sfx_context(cut_name, t):
    """Where plinks and chimes should sit harmonically."""
    if cut_name == "main" and 164.25 <= t < 190.5:
        return "bminor"
    if cut_name == "main" and 218.0 <= t < 226.75:
        return "gates"
    return "dmajor"


def render_sfx(cut):
    n = ns(cut["duration"])
    dry = np.zeros((n, 2))
    send = np.zeros((n, 2))
    log = []
    items = sorted(enumerate(cut["sfx"]), key=lambda p: (p[1]["t"], p[0]))
    run_i, last_plink, lamp_seen = 0, -9.0, False
    for idx, s in items:
        kind, t = s["kind"], s["t"]
        rng = rng_for(cut["name"], idx, kind, t)
        params = {k: v for k, v in s.items() if k not in ("t", "kind")}
        ctx = sfx_context(cut["name"], t)
        if kind == "plink":
            run_i = run_i + 1 if t - last_plink < 0.6 else 0
            last_plink = t
            start = {"bminor": nm("B5"), "gates": nm("A5")}.get(ctx, nm("D6"))
            params["midi"] = penta_from(start, run_i)
        if kind == "plinks":
            start = {"bminor": nm("F#5")}.get(ctx, nm("A5"))
            params["midis"] = [penta_from(start, i) for i in range(int(s.get("n", 3)))]
        if kind == "chime":
            params["pitches"] = (("B4", "F#5") if params.get("soft") else ("F#5", "B5")) \
                if ctx == "bminor" else ("A5", "D6")
        if kind == "lamp":
            params["on"] = not lamp_seen
            lamp_seen = True
        x = SFX[kind](rng, **params)
        target = SFX_TARGET[kind] + SFX_OFFSET - (SOFT_DROP if s.get("soft") else 0)
        g = undb(target - momentary_max(x))
        x = x * g
        pk = np.abs(x).max()
        cap = SFX_PEAK_CAP - (SOFT_DROP if s.get("soft") else 0)
        if pk > undb(cap):
            x *= undb(cap) / pk
        pan = SFX_PAN.get(kind, 0.0) + rng.uniform(-0.12, 0.12)
        add(dry, x, t, pan)
        add(send, x, t, pan, 0.12)
        if kind == "lamp" and params["on"]:
            hum = lamp_hum(ns(0.5)) * undb(-45)
            add(dry, hum, t + 0.03, 0.25)
        log.append((kind, t, len(x) / SR))
    ir = make_ir(0.32, 0.5, 777, predelay=0.004)
    return dry + 0.5 * convolve_st(send, ir), log


# ════════════════════════════════════════════════════════════════════════════
# Voice
# ════════════════════════════════════════════════════════════════════════════

def compress(x, thr_db=-22.0, ratio=2.2, att=0.008, rel=0.12):
    blk = 48
    nb = len(x) // blk + 1
    xp = np.concatenate([x, np.zeros(nb * blk - len(x))])
    rms = np.sqrt(np.mean(xp.reshape(nb, blk) ** 2, axis=1) + 1e-12)
    lvl = db(rms)
    over = np.maximum(0, lvl - thr_db)
    gr = -over * (1 - 1 / ratio)
    a_ = np.exp(-blk / (att * SR))
    r_ = np.exp(-blk / (rel * SR))
    out = np.zeros(nb)
    g = 0.0
    for i in range(nb):
        c = a_ if gr[i] < g else r_
        g = c * g + (1 - c) * gr[i]
        out[i] = g
    gain = np.interp(np.arange(len(x)), np.arange(nb) * blk + blk / 2, out)
    return x * undb(gain)


def render_voice(cut):
    n = ns(cut["duration"])
    v = np.zeros(n)
    for c in cut["cues"]:
        x, sr = sf.read(NARR / f"{c['id']}.wav", dtype="float64")
        assert sr == SR, f"{c['id']}: {sr} Hz"
        if x.ndim > 1:
            x = x.mean(axis=1)
        L = integrated_lufs(np.concatenate([x, np.zeros(max(0, ns(0.45) - len(x)))]))
        g = float(np.clip(-18.0 - L, -4.0, 3.0))
        place(v, x * undb(g), c["start"])
    v = hp(v, 80, 2)
    v = peaking(v, 280, -1.5, 1.0)
    v = peaking(v, 3300, 2.5, 0.9)
    v = peaking(v, 9000, 1.0, 0.7)
    v = compress(v)
    return v


def activity(v, thr_db=-42.0, hold=0.22, look=0.05, att=0.06, rel=0.4):
    """0..1 'voice present' envelope with lookahead, hold, attack and release."""
    blk = 48
    nb = len(v) // blk + 1
    vp = np.concatenate([v, np.zeros(nb * blk - len(v))])
    lvl = db(np.sqrt(np.mean(vp.reshape(nb, blk) ** 2, axis=1) + 1e-12))
    on = (lvl > thr_db).astype(float)
    on = maximum_filter1d(on, int(2 * hold * SR / blk) + 1)
    sh = int(look * SR / blk)
    on = np.concatenate([on[sh:], np.zeros(sh)])
    a_ = np.exp(-blk / (att * SR))
    r_ = np.exp(-blk / (rel * SR))
    out = np.zeros(nb)
    g = 0.0
    for i in range(nb):
        c = a_ if on[i] > g else r_
        g = c * g + (1 - c) * on[i]
        out[i] = g
    return np.interp(np.arange(len(v)), np.arange(nb) * blk + blk / 2, out)


# ════════════════════════════════════════════════════════════════════════════
# Master
# ════════════════════════════════════════════════════════════════════════════

def limiter_gain(peak, ceiling, look=0.0015, release=0.08, blk=16):
    """Gain curve for a lookahead peak limiter: instant attack (spread over the
    lookahead so the gain is already down at the peak), exponential release."""
    nb = len(peak) // blk + 1
    pk = np.pad(peak, (0, nb * blk - len(peak))).reshape(nb, blk).max(axis=1)
    target = np.minimum(1.0, ceiling / np.maximum(pk, 1e-12))
    la = max(1, int(look * SR / blk))
    g1 = minimum_filter1d(target, 2 * la + 1)
    r = np.exp(-blk / (release * SR))
    g = np.empty(nb)
    cur = 1.0
    for i in range(nb):
        v = g1[i]
        cur = v if v < cur else v + r * (cur - v)
        g[i] = cur
    g = uniform_filter1d(g, 2 * la + 1)
    g = np.minimum(g, minimum_filter1d(target, 2 * la + 1))
    return np.interp(np.arange(len(peak)), np.arange(nb) * blk + blk / 2, g)


def tp_limit(x, ceiling_db):
    c = undb(ceiling_db)
    os_ = signal.resample_poly(x, 4, 1, axis=0)
    pk = np.abs(os_).max(axis=1)
    pk = np.pad(pk, (0, (-len(pk)) % 4)).reshape(-1, 4).max(axis=1)[:len(x)]
    g = limiter_gain(pk, c)
    return x * g[:, None], float(db(g.min())), g


def voice_peak_control(v, ceiling_db):
    """Gentle peak control on the voice bus only (keeps the master limiter idle)."""
    g = limiter_gain(np.abs(v), undb(ceiling_db), look=0.002, release=0.06)
    return v * g


def duck_profile(cut, n, scene_depths):
    """Per-sample music duck depth (dB at full voice activity): DUCK_DB_MUSIC,
    deepened inside the scenes listed in scene_depths, with 0.6 s crossfades."""
    t = tvec(n)
    d = np.full(n, DUCK_DB_MUSIC)
    xf = 0.6
    for s in cut["scenes"]:
        if s["id"] not in scene_depths:
            continue
        a, b, deep = s["start"], s["end"], scene_depths[s["id"]]
        w = np.clip(np.minimum((t - (a - xf)) / xf, ((b + xf) - t) / xf), 0, 1)
        w = np.sin(w * np.pi / 2) ** 2
        d = d + (deep - DUCK_DB_MUSIC) * w
    return d


def cue_margins(cut, voice, music, ids=None):
    """Voice-over-music margin per cue: (K-weighted LU difference, RMS dB difference)."""
    vp, mp = kpower(voice), kpower(music)
    out = {}
    for c in cut["cues"]:
        if ids and c["id"] not in ids:
            continue
        s0, s1 = ns(c["start"]), ns(c["end"])
        lk = 10 * np.log10((vp[s0:s1].mean() + 1e-20) / (mp[s0:s1].mean() + 1e-20))
        rv = np.sqrt(np.mean(voice[s0:s1] ** 2))
        rm = np.sqrt(np.mean(music[s0:s1] ** 2))
        out[c["id"]] = (float(lk), float(db(rv) - db(rm)), float(db(rm)))
    return out


# Scenes where the music ducks deeper than DUCK_DB_MUSIC under speech (main cut).
# The felt piano in Operating Limitations sits in the voice's range, so it gets
# a deeper duck; build() deepens it further if any cue there is under the margin.
SCENE_DUCK = {"main": {"limits": -15.0}}
MIN_MARGIN_DB = 12.0


def master(voice, music, sfx, act, duck_db=None):
    v2 = np.stack([voice, voice], axis=1)
    v2 *= undb(VOICE_LUFS - integrated_lufs(v2))
    v2 = np.stack([voice_peak_control(v2[:, 0], VOICE_LUFS + 14.0)] * 2, axis=1)
    music = music * undb(MUSIC_LUFS - integrated_lufs(music))
    depth = DUCK_DB_MUSIC if duck_db is None else duck_db
    music = music * undb(depth * act)[:, None]
    sfx = sfx * undb(DUCK_DB_SFX * act)[:, None]
    mix = v2 + music + sfx
    gain = 1.0
    for _ in range(4):
        gain *= undb(TARGET_LUFS - integrated_lufs(mix * gain))
        out, gr, g = tp_limit(mix * gain, CEILING_DBTP)
        if abs(integrated_lufs(out) - TARGET_LUFS) < 0.1:
            break
    lim = g[:, None]
    return out, v2 * gain * lim, music * gain * lim, sfx * gain * lim, gr, g


# ════════════════════════════════════════════════════════════════════════════
# QA, encode, spectrogram
# ════════════════════════════════════════════════════════════════════════════

def ffmpeg_ebur(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-filter_complex",
                        "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True)
    txt = r.stderr[r.stderr.rfind("Summary:"):]
    I = re.search(r"I:\s+(-?[\d.]+) LUFS", txt)
    P = re.search(r"Peak:\s+(-?[\d.inf]+) dBFS", txt)
    LRA = re.search(r"LRA:\s+(-?[\d.]+) LU", txt)
    return (float(I.group(1)) if I else None, float(P.group(1)) if P else None,
            float(LRA.group(1)) if LRA else None)


def probe_duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                        "default=nw=1:nk=1", str(path)], capture_output=True, text=True)
    return float(r.stdout.strip())


def encode(wav, m4a):
    m4a.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(wav),
                    "-c:a", "aac", "-profile:a", "aac_low", "-b:a", "160k", "-ar", str(SR),
                    "-ac", "2", "-movflags", "+faststart", str(m4a)], check=True)


def spectrogram(x, cut, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    mono = x.mean(axis=1)
    f, t, Sxx = signal.spectrogram(mono, SR, nperseg=2048, noverlap=1024, scaling="spectrum")
    keep = f <= 12000
    fig, ax = plt.subplots(figsize=(22, 6), dpi=110)
    ax.pcolormesh(t, f[keep], 10 * np.log10(Sxx[keep] + 1e-14), shading="auto",
                  cmap="magma", vmin=-110, vmax=-30)
    ax.set_yscale("symlog", linthresh=500)
    ax.set_ylim(40, 12000)
    for s in cut["scenes"]:
        ax.axvline(s["start"], color="w", lw=0.6, alpha=0.6)
        ax.text(s["start"] + 0.5, 9000, s["id"], color="w", fontsize=8)
    for c in cut["cues"]:
        ax.plot([c["start"], c["end"]], [45, 45], color="cyan", lw=3)
    ax.set_xlabel("seconds")
    ax.set_ylabel("Hz")
    ax.set_title(f"{cut['name']} master")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def qa(cut, mix, voice, music, sfx, log, drop, gr):
    name = cut["name"]
    print(f"\n── QA: {name} ──")
    assert np.isfinite(mix).all(), "NaN/inf in master"
    print(f"  duration        {len(mix) / SR:.3f} s (timeline {cut['duration']:.3f})")
    print(f"  integrated      {integrated_lufs(mix):.2f} LUFS (internal BS.1770)")
    print(f"  true peak       {true_peak_db(mix):.2f} dBTP (4x oversampled); limiter max GR {gr:.2f} dB")
    print(f"  sample peak     {db(np.abs(mix).max()):.2f} dBFS")
    a, b = drop
    i0, i1 = ns(cue(cut, "s5h")["start"]), ns(cue(cut, "s5i")["end"])
    seg = music[i0:i1]
    print(f"  music RMS s5h..s5i ({i0 / SR:.2f}-{i1 / SR:.2f})  {db(np.sqrt(np.mean(seg ** 2))):.1f} dBFS")
    # sfx table
    print("  sfx events (kind, t, peak dBFS in master sfx stem):")
    rows = []
    for kind, t, d in log:
        s0, s1 = ns(t), ns(t + max(0.06, min(d, 1.5)))
        pk = db(np.abs(sfx[s0:s1]).max()) if s1 > s0 else -120
        rows.append(f"{kind:>10} {t:7.2f} {pk:6.1f}")
        if pk < -60:
            print(f"   !! no energy for {kind} at {t}")
    for i in range(0, len(rows), 4):
        print("   " + " | ".join(rows[i:i + 4]))
    # music bed continuity (2 s windows)
    p = kpower(music)
    starts, L = window_lufs(p, 2.0, 2.0)
    gaps = [(s / SR, l) for s, l in zip(starts, L)
            if l < -50 and not (a - 2 < s / SR < b) and s / SR < cut["duration"] - 3]
    print("  music short-term (2 s windows): min %.1f, median %.1f, max %.1f LUFS"
          % (L.min(), np.median(L), L.max()))
    print("  music gaps (<-50 LUFS, excl. drop/tail):", "none" if not gaps else
          ", ".join(f"{t:.0f}s({l:.0f})" for t, l in gaps))
    vp = kpower(voice)
    act = []
    ev_, em_ = 0.0, 0.0
    for c in cut["cues"]:
        s0, s1 = ns(c["start"]), ns(c["end"])
        ev_ += vp[s0:s1].sum()
        em_ += p[s0:s1].sum()
        lv = -0.691 + 10 * np.log10(vp[s0:s1].mean() + 1e-20)
        lm = -0.691 + 10 * np.log10(p[s0:s1].mean() + 1e-20)
        act.append((c["id"], min(lv - lm, 60.0)))
    r = np.array([x[1] for x in act])
    worst = min(act, key=lambda x: x[1])
    print(f"  voice-to-music under speech: energy ratio {10 * np.log10(ev_ / em_):.1f} dB, "
          f"per-cue median {np.median(r):.1f} dB, min {worst[1]:.1f} dB ({worst[0]})")
    # music alone level
    alone = ~(activity(voice.mean(axis=1)) > 0.05)
    st, Ls = window_lufs(p * alone, 3.0, 1.0)
    frac = np.array([alone[s:s + ns(3.0)].mean() for s in st])
    sel = Ls[(frac > 0.99) & (Ls > -60)]
    if len(sel):
        print(f"  music alone, short-term 3 s: median {np.median(sel):.1f} LUFS "
              f"(p10 {np.percentile(sel, 10):.1f}, p90 {np.percentile(sel, 90):.1f})")


def build(cut, only_score=False):
    name = cut["name"]
    t0 = time.time()
    n = ns(cut["duration"])
    S = score_main(cut) if name == "main" else score_pre60(cut)
    drop = drop_window(cut)
    fade_end = (cut["duration"] - 2.6, cut["duration"] - 1.05)
    music, stats = render_music(S, n, drop, fade_end)
    print(f"[{name}] music: {len(S.ev)} notes {stats} ({time.time() - t0:.1f}s)")
    sfx, log = render_sfx(cut)
    print(f"[{name}] sfx: {len(log)} events ({time.time() - t0:.1f}s)")
    voice = render_voice(cut)
    act = activity(voice)
    depths = dict(SCENE_DUCK.get(name, {}))
    for _ in range(6):
        duck = duck_profile(cut, n, depths) if depths else None
        mix, v2, m2, s2, gr, lg = master(voice, music, sfx, act, duck)
        short = 0.0
        for sid in depths:
            sc = next(s for s in cut["scenes"] if s["id"] == sid)
            ids = [c["id"] for c in cut["cues"] if sc["start"] <= c["start"] < sc["end"]]
            mg = cue_margins(cut, v2, m2, ids)
            worst = min(min(lk, rr) for lk, rr, _ in mg.values())
            if worst < MIN_MARGIN_DB + 0.5:
                depths[sid] -= (MIN_MARGIN_DB + 0.5 - worst) + 0.5
                short = max(short, MIN_MARGIN_DB + 0.5 - worst)
        if short == 0.0:
            break
    if depths:
        print(f"[{name}] scene duck depths: {depths}")
        for sid in depths:
            sc = next(s for s in cut["scenes"] if s["id"] == sid)
            ids = [c["id"] for c in cut["cues"] if sc["start"] <= c["start"] < sc["end"]]
            for cid, (lk, rr, rm) in cue_margins(cut, v2, m2, ids).items():
                print(f"   {sid} {cid}: voice over music {lk:5.1f} LU (K-wtd), {rr:5.1f} dB RMS; "
                      f"music {rm:6.1f} dBFS RMS")
    hot = np.where(lg < undb(-1.0))[0]
    print(f"[{name}] limiter >1 dB on {len(hot) / SR * 1000:.0f} ms total"
          + (f", worst at {np.argmin(lg) / SR:.2f}s" if len(hot) else ""))
    OUT.mkdir(parents=True, exist_ok=True)
    STEMS.mkdir(parents=True, exist_ok=True)
    wav = OUT / f"{name}.wav"
    sf.write(wav, mix.astype(np.float32), SR, subtype="FLOAT")
    for stem, x in (("voice", v2), ("music", m2), ("sfx", s2)):
        sf.write(STEMS / f"{name}-{stem}.wav", x.astype(np.float32), SR, subtype="FLOAT")
    m4a = ASSETS / M4A[name]
    encode(wav, m4a)
    qa(cut, mix, v2, m2, s2, log, drop, gr)
    I, P, LRA = ffmpeg_ebur(wav)
    I2, P2, _ = ffmpeg_ebur(m4a)
    d = probe_duration(m4a)
    print(f"  ffmpeg ebur128 wav: I {I} LUFS, TP {P} dBTP, LRA {LRA} LU")
    print(f"  ffmpeg ebur128 m4a: I {I2} LUFS, TP {P2} dBTP; duration {d:.3f} s "
          f"(Δ {1000 * (d - cut['duration']):+.0f} ms)")
    if name == "main":
        spectrogram(mix, cut, OUT / "main-spectrogram.png")
    print(f"[{name}] done in {time.time() - t0:.1f}s")
    return dict(I=I, TP=P, I_m4a=I2, TP_m4a=P2, dur=d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cut", choices=["main", "preflight60"], default=None)
    args = ap.parse_args()
    tl = json.loads(TIMELINE.read_text())
    for name in ("main", "preflight60"):
        if args.cut and name != args.cut:
            continue
        cut = dict(tl[name])
        cut["name"] = name
        build(cut)


if __name__ == "__main__":
    main()
