"""家具の立体の絵（カタログ用）を作る

  python3 tools/render_preview.py <バニラのテクスチャのフォルダ> <出力フォルダ>

モデル（JSON）の箱を、テクスチャを貼って斜め上から見た絵にする。
"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
A = f"{ROOT}/src/main/resources/assets/jsn_furniture"
VANILLA = sys.argv[1]
OUT = sys.argv[2]
SIZE = 200
os.makedirs(OUT, exist_ok=True)

F = np.array([1.0, -0.75, 1.0]); F /= np.linalg.norm(F)
R = np.cross(F, [0, 1, 0]); R /= np.linalg.norm(R)
U = np.cross(R, F)
SHADE = {"up": 1.0, "north": 0.82, "west": 0.66, "south": 0.82, "east": 0.66, "down": 0.5}
NORMAL = {"north": (0, 0, -1), "south": (0, 0, 1), "west": (-1, 0, 0), "east": (1, 0, 0), "up": (0, 1, 0), "down": (0, -1, 0)}
_tex = {}


def tex(ref):
    if ref in _tex:
        return _tex[ref]
    ns, path = ref.split(":") if ":" in ref else ("minecraft", ref)
    p = f"{VANILLA}/{path.split('/', 1)[1]}.png" if ns == "minecraft" else f"{A}/textures/{path}.png"
    try:
        im = Image.open(p).convert("RGBA")
        im = im.crop((0, 0, im.width, im.width))
    except FileNotFoundError:
        im = Image.new("RGBA", (16, 16), (255, 0, 255, 255))
    _tex[ref] = im
    return im


def corners(f, t):
    x1, y1, z1 = f
    x2, y2, z2 = t
    return {
        "north": [(x2, y2, z1), (x1, y2, z1), (x1, y1, z1), (x2, y1, z1)],
        "south": [(x1, y2, z2), (x2, y2, z2), (x2, y1, z2), (x1, y1, z2)],
        "west": [(x1, y2, z1), (x1, y2, z2), (x1, y1, z2), (x1, y1, z1)],
        "east": [(x2, y2, z2), (x2, y2, z1), (x2, y1, z1), (x2, y1, z2)],
        "up": [(x1, y2, z1), (x2, y2, z1), (x2, y2, z2), (x1, y2, z2)],
        "down": [(x1, y1, z2), (x2, y1, z2), (x2, y1, z1), (x1, y1, z1)],
    }


def rot_fn(rot):
    if not rot:
        return lambda p: np.array(p, float)
    o = np.array(rot["origin"], float)
    a = np.radians(rot["angle"])
    c, s = np.cos(a), np.sin(a)
    ax = rot["axis"]
    if ax == "y":
        M = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    elif ax == "x":
        M = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    else:
        M = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    return lambda p: M @ (np.array(p, float) - o) + o


def resolve(textures, key):
    v = textures.get(key, key)
    seen = 0
    while v.startswith("#") and seen < 5:
        v = textures.get(v[1:], v)
        seen += 1
    return v


def faces_of(model, offset=(0, 0, 0)):
    out = []
    tx = model.get("textures", {})
    for e in model.get("elements", []):
        f = np.array(e["from"], float) + offset
        t = np.array(e["to"], float) + offset
        rf = rot_fn(e.get("rotation") and {**e["rotation"], "origin": list(np.array(e["rotation"]["origin"]) + offset)})
        cs = corners(f, t)
        for name, fc in e["faces"].items():
            pts = [rf(p) for p in cs[name]]
            n = np.cross(pts[1] - pts[0], pts[3] - pts[0])
            if np.linalg.norm(n) < 1e-6:
                n = np.array(NORMAL[name], float)
            # 板（厚みなし）は両面見せる
            flat = np.allclose(f[0], t[0]) or np.allclose(f[1], t[1]) or np.allclose(f[2], t[2])
            if not flat and np.dot(-n, F) >= 0:
                continue
            uv = fc.get("uv") or [0, 0, 16, 16]
            out.append((pts, uv, resolve(tx, fc["texture"][1:]), SHADE[name]))
    return out


def render(faces, path):
    proj = []
    for pts, uv, ref, sh in faces:
        sp = [(float(np.dot(p, R)), float(-np.dot(p, U))) for p in pts]
        depth = float(np.mean([np.dot(p, F) for p in pts]))
        proj.append((depth, sp, uv, ref, sh))
    if not proj:
        return
    xs = [x for _, sp, *_ in proj for x, _ in sp]
    ys = [y for _, sp, *_ in proj for _, y in sp]
    w, h = max(xs) - min(xs), max(ys) - min(ys)
    scale = min((SIZE - 24) / max(w, 1), (SIZE - 24) / max(h, 1), 7.5)
    ox = SIZE / 2 - (min(xs) + w / 2) * scale
    oy = SIZE / 2 - (min(ys) + h / 2) * scale
    canvas = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    for depth, sp, uv, ref, sh in sorted(proj, key=lambda q: -q[0]):
        P = [(x * scale + ox, y * scale + oy) for x, y in sp]
        T = tex(ref)
        k = T.width / 16.0
        u1, v1, u2, v2 = uv
        src = [(u1 * k, v1 * k), (u2 * k, v1 * k), (u1 * k, v2 * k)]
        dst = [P[0], P[1], P[3]]
        M = np.array([[dst[i][0], dst[i][1], 1] for i in range(3)])
        if abs(np.linalg.det(M)) < 1e-6:
            continue
        cu = np.linalg.solve(M, [s[0] for s in src])
        cv = np.linalg.solve(M, [s[1] for s in src])
        bx0, by0 = int(min(p[0] for p in P)) - 1, int(min(p[1] for p in P)) - 1
        bx1, by1 = int(max(p[0] for p in P)) + 2, int(max(p[1] for p in P)) + 2
        bw, bh = max(1, bx1 - bx0), max(1, by1 - by0)
        coeffs = (cu[0], cu[1], cu[0] * bx0 + cu[1] * by0 + cu[2], cv[0], cv[1], cv[0] * bx0 + cv[1] * by0 + cv[2])
        # はみ出し防止に、テクスチャを1つ分の周りにくり返す
        big = Image.new("RGBA", (T.width * 3, T.height * 3))
        for i in range(3):
            for j in range(3):
                big.paste(T, (i * T.width, j * T.height))
        coeffs = (coeffs[0], coeffs[1], coeffs[2] + T.width, coeffs[3], coeffs[4], coeffs[5] + T.height)
        face = big.transform((bw, bh), Image.AFFINE, coeffs, resample=Image.NEAREST)
        if sh != 1.0:
            r, g, b, a = face.split()
            r = r.point(lambda v: int(v * sh)); g = g.point(lambda v: int(v * sh)); b = b.point(lambda v: int(v * sh))
            face = Image.merge("RGBA", (r, g, b, a))
        mask = Image.new("L", (bw, bh), 0)
        ImageDraw.Draw(mask).polygon([(x - bx0, y - by0) for x, y in P], fill=255)
        alpha = Image.fromarray((np.array(face.split()[3], float) * np.array(mask, float) / 255).astype("uint8"))
        face.putalpha(alpha)
        canvas.alpha_composite(face, (bx0, by0)) if bx0 >= 0 and by0 >= 0 else canvas.paste(face, (bx0, by0), face)
    canvas.save(path)


def load(name):
    with open(f"{A}/models/{name}.json", encoding="utf-8") as f:
        return json.load(f)


specs = json.load(open(f"{ROOT}/src/main/resources/jsn_furniture_specs.json", encoding="utf-8"))
ids = [s["id"] for s in specs["furniture"]] + [b["id"] for b in specs["beds"]]
for i in ids:
    render(faces_of(load(f"item/{i}")), f"{OUT}/{i}.png")
# 障子・ふすま：2マスの板
for d in [x["id"] for x in specs["doors"]]:
    m = {"textures": {"b": f"jsn_furniture:block/{d}_bottom", "t": f"jsn_furniture:block/{d}_top"}, "elements": [
        {"from": [0, 0, 13], "to": [16, 16, 16], "faces": {k: {"texture": "#b", "uv": [0, 0, 16, 16] if k in ("north", "south") else [0, 0, 3, 16]} for k in ("north", "west", "up")}},
        {"from": [0, 16, 13], "to": [16, 32, 16], "faces": {k: {"texture": "#t", "uv": [0, 0, 16, 16] if k in ("north", "south") else [0, 0, 3, 16]} for k in ("north", "west", "up")}}]}
    render(faces_of(m), f"{OUT}/{d}.png")
print(len(ids) + len(specs["doors"]), "枚")
