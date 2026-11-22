"""風鈴・鹿威しの音を作る

  python3 tools/gen_sounds.py  →  assets/jsn_furniture/sounds/*.ogg と sounds.json
"""
import json, os, subprocess, tempfile, wave
import numpy as np

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
A = f"{ROOT}/src/main/resources/assets/jsn_furniture"
SR = 44100
rng = np.random.default_rng(7)


def t_axis(sec):
    return np.arange(int(SR * sec)) / SR


def bell(base, partials, sec, decay, bright=1.0, wobble=0.0):
    """鐘の音：倍音（整数倍でない）を重ねて、それぞれ減衰させる"""
    t = t_axis(sec)
    out = np.zeros_like(t)
    for ratio, amp, dk in partials:
        f = base * ratio
        trem = 1 + wobble * np.sin(2 * np.pi * (3 + rng.random() * 3) * t)
        out += amp * np.sin(2 * np.pi * f * t + rng.random() * 6) * np.exp(-t * decay * dk) * trem
    # 打った瞬間のカチッ
    click = rng.normal(0, 1, len(t)) * np.exp(-t * 400) * 0.3 * bright
    out += click
    return out


def strike_series(fn, hits, sec):
    """風でゆれて何回か当たる"""
    total = np.zeros(int(SR * sec))
    for at, vel in hits:
        s = fn() * vel
        i = int(at * SR)
        n = min(len(s), len(total) - i)
        total[i:i + n] += s[:n]
    return total


def glass(base):
    return lambda: bell(base, [(1, 1.0, 1.0), (2.76, 0.5, 1.6), (5.4, 0.25, 2.4), (8.9, 0.12, 3.5), (1.5, 0.2, 1.2)], 2.6, 2.2, 1.2, 0.04)


def iron(base):
    return lambda: bell(base, [(1, 1.0, 1.0), (2.32, 0.6, 1.2), (4.25, 0.35, 1.6), (6.8, 0.15, 2.2), (1.01, 0.5, 0.9)], 4.5, 0.9, 0.8, 0.06)


def brass(base):
    return lambda: bell(base, [(1, 1.0, 1.0), (2.4, 0.55, 1.3), (3.9, 0.3, 1.8), (5.6, 0.2, 2.3)], 3.5, 1.3, 1.0, 0.05)


def ceramic(base):
    return lambda: bell(base, [(1, 1.0, 1.0), (2.9, 0.35, 2.0), (6.1, 0.12, 3.0)], 1.2, 5.0, 1.5, 0.0)


def bamboo_hit(base):
    def f():
        t = t_axis(0.5)
        body = np.sin(2 * np.pi * base * t) * np.exp(-t * 28) + 0.5 * np.sin(2 * np.pi * base * 2.7 * t) * np.exp(-t * 40)
        noise = rng.normal(0, 1, len(t)) * np.exp(-t * 120) * 0.6
        return body + noise
    return f


def shishi():
    """鹿威し：竹が石を打つ「コーン」"""
    t = t_axis(1.6)
    base = 380
    body = (np.sin(2 * np.pi * base * t) * np.exp(-t * 7) + 0.6 * np.sin(2 * np.pi * base * 2.02 * t) * np.exp(-t * 10)
            + 0.3 * np.sin(2 * np.pi * base * 3.1 * t) * np.exp(-t * 16))
    hit = rng.normal(0, 1, len(t)) * np.exp(-t * 90) * 0.8
    # 水がこぼれる音（あとから少し）
    water = rng.normal(0, 1, len(t))
    water = np.convolve(water, np.ones(30) / 30, mode="same") * np.exp(-((t - 0.25) ** 2) / 0.02) * 0.6
    return body + hit + water


def write(name, data):
    data = data / (np.max(np.abs(data)) + 1e-9) * 0.85
    pcm = (data * 32767).astype(np.int16)
    os.makedirs(f"{A}/sounds", exist_ok=True)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        path = tmp.name
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-c:a", "libvorbis", "-q:a", "4", f"{A}/sounds/{name}.ogg"], check=True)
    os.remove(path)


SOUNDS = {}


def make(event, variants):
    names = []
    for i, data in enumerate(variants):
        n = f"{event}_{i + 1}"
        write(n, data)
        names.append(f"jsn_furniture:{n}")
    SOUNDS[event] = {"subtitle": f"subtitles.jsn_furniture.{event}", "sounds": names}


make("furin_glass", [strike_series(glass(b), h, 3.2) for b, h in (
    (2350, [(0, 1.0)]), (2600, [(0, 0.9), (0.45, 0.6)]), (2150, [(0, 0.8), (0.3, 0.5), (0.75, 0.35)]))])
make("furin_iron", [strike_series(iron(b), h, 5.0) for b, h in ((1320, [(0, 1.0)]), (1180, [(0, 0.9), (0.6, 0.55)]))])
make("furin_brass", [strike_series(brass(b), h, 4.0) for b, h in ((1650, [(0, 1.0)]), (1500, [(0, 0.8), (0.5, 0.5)]))])
make("furin_ceramic", [strike_series(ceramic(b), h, 1.8) for b, h in ((1900, [(0, 1.0)]), (2100, [(0, 0.8), (0.35, 0.5)]))])
make("furin_bamboo", [strike_series(bamboo_hit(b), h, 1.4) for b, h in (
    (620, [(0, 1.0), (0.12, 0.6), (0.3, 0.7), (0.5, 0.4)]), (540, [(0, 0.9), (0.2, 0.8), (0.33, 0.5)]))])
make("shishi_odoshi", [shishi()])

with open(f"{A}/sounds.json", "w", encoding="utf-8") as f:
    json.dump(SOUNDS, f, indent=1)
print("音:", ", ".join(SOUNDS))
