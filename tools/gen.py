"""jsn-Furniture のデータを全部作る

  python3 tools/gen.py

・家具の一覧（specs.json：Java がこれを読んでブロックを登録する）
・モデル・ブロックの状態・アイテムモデル・テクスチャ
・名前（日本語・英語）・レシピ・ドロップ・道具タグ
（音は tools/gen_sounds.py）
"""
import json, math, os, random, shutil
from PIL import Image, ImageDraw

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
RES = f"{ROOT}/src/main/resources"
A = f"{RES}/assets/jsn_furniture"
D = f"{RES}/data/jsn_furniture"
NS = "jsn_furniture"

for p in (f"{A}/blockstates", f"{A}/models", f"{D}/recipe", f"{D}/loot_table"):
    shutil.rmtree(p, ignore_errors=True)


def wj(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.write("\n")


def save(im, name):
    p = f"{A}/textures/{name}.png"
    os.makedirs(os.path.dirname(p), exist_ok=True)
    im.save(p)


def hx(s):
    s = s.lstrip("#")
    return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), 255)


def shade(c, f):
    return tuple(max(0, min(255, int(v * f))) for v in c[:3]) + (255,)


# ============================================================ 木・色

WOODS = [
    ("oak", "オーク", "Oak"), ("spruce", "トウヒ", "Spruce"), ("birch", "シラカバ", "Birch"),
    ("jungle", "ジャングル", "Jungle"), ("acacia", "アカシア", "Acacia"), ("dark_oak", "ダークオーク", "Dark Oak"),
    ("mangrove", "マングローブ", "Mangrove"), ("cherry", "サクラ", "Cherry"), ("bamboo", "竹", "Bamboo"),
    ("crimson", "真紅", "Crimson"), ("warped", "歪み", "Warped"),
]


def wood_tex(w):
    if w in ("crimson", "warped"):
        log, strip = f"{w}_stem", f"stripped_{w}_stem"
    elif w == "bamboo":
        log, strip = "bamboo_block", "stripped_bamboo_block"
    else:
        log, strip = f"{w}_log", f"stripped_{w}_log"
    return {"p": f"minecraft:block/{w}_planks", "l": f"minecraft:block/{log}", "lt": f"minecraft:block/{log}_top",
            "s": f"minecraft:block/{strip}"}


def wood_items(w):
    log = f"{w}_stem" if w in ("crimson", "warped") else ("bamboo_block" if w == "bamboo" else f"{w}_log")
    return {"P": f"minecraft:{w}_planks", "L": f"minecraft:{log}", "H": f"minecraft:{w}_slab"}


COLORS = [
    ("white", "白", "White"), ("orange", "橙", "Orange"), ("magenta", "赤紫", "Magenta"),
    ("light_blue", "空色", "Light Blue"), ("yellow", "黄色", "Yellow"), ("lime", "黄緑", "Lime"),
    ("pink", "桃色", "Pink"), ("gray", "灰色", "Gray"), ("light_gray", "薄灰色", "Light Gray"),
    ("cyan", "青緑", "Cyan"), ("purple", "紫", "Purple"), ("blue", "青", "Blue"), ("brown", "茶色", "Brown"),
    ("green", "緑", "Green"), ("red", "赤", "Red"), ("black", "黒", "Black"),
]
DYE_RGB = {
    "white": "#f0f0f0", "orange": "#f07613", "magenta": "#bd44b3", "light_blue": "#3aafd9", "yellow": "#f8c527",
    "lime": "#70b919", "pink": "#ed8dac", "gray": "#3e4447", "light_gray": "#8e8e86", "cyan": "#158991",
    "purple": "#792aac", "blue": "#35399d", "brown": "#724728", "green": "#546d1b", "red": "#a12722", "black": "#141519",
}

# ============================================================ モデルの部品

FACES = ("north", "south", "east", "west", "up", "down")


def auto_uv(face, f, t):
    x1, y1, z1 = f
    x2, y2, z2 = t
    if face == "north":
        u = [16 - x2, 16 - y2, 16 - x1, 16 - y1]
    elif face == "south":
        u = [x1, 16 - y2, x2, 16 - y1]
    elif face == "east":
        u = [16 - z2, 16 - y2, 16 - z1, 16 - y1]
    elif face == "west":
        u = [z1, 16 - y2, z2, 16 - y1]
    elif face == "up":
        u = [x1, z1, x2, z2]
    else:
        u = [x1, 16 - z2, x2, 16 - z1]
    # 16 を超えたり負になったりしたら、絵がはみ出さないようにずらす
    for a, b in ((0, 2), (1, 3)):
        lo = min(u[a], u[b])
        hi = max(u[a], u[b])
        while lo < 0:
            u[a] += 16
            u[b] += 16
            lo += 16
            hi += 16
        while hi > 16:
            u[a] -= 16
            u[b] -= 16
            lo -= 16
            hi -= 16
        if lo < 0 or hi > 16:
            u[a], u[b] = (0, min(16, abs(u[b] - u[a]))) if u[a] <= u[b] else (min(16, abs(u[b] - u[a])), 0)
    return [round(v, 3) for v in u]


class E:
    """モデルの箱1つ。shape=False なら当たり判定に入れない（飾りの部分）"""

    def __init__(self, f, t, tex, shape=True, faces=None, rot=None, tint=None, uv=None):
        self.f = list(f)
        self.t = list(t)
        self.tex = tex
        self.shape = shape
        self.faces = faces or FACES
        self.rot = rot
        self.uv = uv or {}

    def json(self, dy=0):
        f = [self.f[0], self.f[1] + dy, self.f[2]]
        t = [self.t[0], self.t[1] + dy, self.t[2]]
        faces = {}
        for fc in self.faces:
            tex = self.tex[fc] if isinstance(self.tex, dict) else self.tex
            if tex is None:
                continue
            uv = self.uv.get(fc) or auto_uv(fc, f, t)
            faces[fc] = {"texture": "#" + tex, "uv": uv}
        e = {"from": f, "to": t, "faces": faces}
        if self.rot:
            e["rotation"] = self.rot
        return e


def b(x1, y1, z1, x2, y2, z2, tex, **kw):
    return E((x1, y1, z1), (x2, y2, z2), tex, **kw)


def cross(x1, y1, x2, y2, tex, z=8, shape=False):
    """× 字の板（炎・草など）"""
    out = []
    for ang in (45, -45):
        out.append(E((x1, y1, z), (x2, y2, z), tex, shape=shape, faces=("north", "south"),
                     rot={"origin": [8, 8, 8], "axis": "y", "angle": ang},
                     uv={"north": [x1, 16 - y2, x2, 16 - y1], "south": [x1, 16 - y2, x2, 16 - y1]}))
    return out


def legs(x1, z1, x2, z2, h, tex, t=2):
    return [b(x1, 0, z1, x1 + t, h, z1 + t, tex), b(x2 - t, 0, z1, x2, h, z1 + t, tex),
            b(x1, 0, z2 - t, x1 + t, h, z2, tex), b(x2 - t, 0, z2 - t, x2, h, z2, tex)]


def model_json(elements, textures, dy=0, lo=None, hi=None, parent="minecraft:block/block", display=None, render_type="minecraft:cutout"):
    els = []
    for e in elements:
        if lo is not None:
            # 高さで切る（2マスの家具の上・下）
            y1, y2 = e.f[1], e.t[1]
            if y2 <= lo or y1 >= hi:
                continue
            c = E((e.f[0], max(y1, lo), e.f[2]), (e.t[0], min(y2, hi), e.t[2]), e.tex, faces=e.faces, rot=e.rot,
                  uv=e.uv if (y1 >= lo and y2 <= hi) else {})
            els.append(c.json(dy))
        else:
            els.append(e.json(dy))
    tx = dict(textures)
    if "particle" not in tx:
        tx["particle"] = next(iter(textures.values()))
    m = {"parent": parent, "textures": tx, "elements": els, "render_type": render_type}
    if display:
        m["display"] = display
    return m


TALL_DISPLAY = {
    "gui": {"rotation": [30, 225, 0], "translation": [0, -3, 0], "scale": [0.4, 0.4, 0.4]},
    "ground": {"rotation": [0, 0, 0], "translation": [0, 3, 0], "scale": [0.2, 0.2, 0.2]},
    "fixed": {"rotation": [0, 0, 0], "translation": [0, -4, 0], "scale": [0.4, 0.4, 0.4]},
    "thirdperson_righthand": {"rotation": [75, 45, 0], "translation": [0, 2.5, 0], "scale": [0.3, 0.3, 0.3]},
    "firstperson_righthand": {"rotation": [0, 45, 0], "translation": [0, 0, 0], "scale": [0.3, 0.3, 0.3]},
    "firstperson_lefthand": {"rotation": [0, 225, 0], "translation": [0, 0, 0], "scale": [0.3, 0.3, 0.3]},
}

# ============================================================ 家具の一覧

SPECS = []   # Java に渡す
LANG_JA = {}
LANG_EN = {}
RECIPES = []  # (id, count, pattern, keys)


class F:
    def __init__(self, id, ja, en, kind, els, tex, tab="west", tall=False, full=False, seat=-1, rows=0, light=0,
                 sound="wood", wall=False, particles="", on=None, open_els=None, tilt_els=None, body=None,
                 furin="", tool="axe", passable=False, hanging=False, recipe=None, count=1):
        self.__dict__.update(locals())
        del self.__dict__["self"]


def add(fur):
    SPECS.append(fur)
    LANG_JA[f"block.{NS}.{fur.id}"] = fur.ja
    LANG_EN[f"block.{NS}.{fur.id}"] = fur.en
    if fur.recipe:
        pat, keys = fur.recipe
        RECIPES.append((fur.id, fur.count, pat, keys))


# ------------------------------------------------------------ 木の家具（11種類）

def chair(T):
    return legs(3, 3, 13, 13, 8, "s") + [
        b(2, 8, 2, 14, 10, 14, "p"),
        b(3, 10, 12, 4, 21, 13, "s", shape=False), b(12, 10, 12, 13, 21, 13, "s", shape=False),
        b(2, 16, 12, 14, 21, 14, "p", shape=False), b(4, 11, 12, 12, 13, 13, "p", shape=False),
    ]


def stool(T):
    return legs(4, 4, 12, 12, 9, "s") + [b(3, 9, 3, 13, 11, 13, "p"), b(5, 4, 4, 11, 5, 5, "s"), b(5, 4, 11, 11, 5, 12, "s")]


def bench(T):
    return [b(1, 0, 3, 3, 7, 13, "s"), b(13, 0, 3, 15, 7, 13, "s"), b(0, 7, 3, 16, 9, 13, "p"), b(3, 3, 7, 13, 4, 9, "s")]


def table(T):
    return legs(1, 1, 15, 15, 14, "s") + [b(0, 14, 0, 16, 16, 16, "p"), b(3, 12, 1, 13, 14, 2, "p"), b(3, 12, 14, 13, 14, 15, "p")]


def coffee_table(T):
    return legs(2, 2, 14, 14, 7, "s") + [b(1, 7, 1, 15, 9, 15, "p"), b(3, 2, 3, 13, 3, 13, "p")]


def desk(T):
    return [b(0, 14, 0, 16, 16, 16, "p"), b(0, 0, 1, 7, 14, 15, "p"), b(14, 0, 1, 16, 14, 3, "s"), b(14, 0, 13, 16, 14, 15, "s"),
            b(1, 9, 0.5, 6, 13, 1, "s", shape=False), b(1, 4, 0.5, 6, 8, 1, "s", shape=False),
            b(3, 10.5, 0, 4, 11.5, 0.5, "m", shape=False), b(3, 5.5, 0, 4, 6.5, 0.5, "m", shape=False)]


def shelf(T):
    return [b(0, 9, 6, 16, 11, 16, "p"), b(2, 5, 14, 4, 9, 16, "s"), b(12, 5, 14, 14, 9, 16, "s"),
            b(2, 6, 12, 4, 9, 14, "s", shape=False), b(12, 6, 12, 14, 9, 14, "s", shape=False)]


def cabinet(T):
    els = [b(1, 0, 2, 15, 16, 15, "p"), b(1, 0, 1, 15, 1, 2, "s")]
    for y in (2, 7, 12):
        els.append(b(2, y, 1, 14, y + 4, 2, "s", shape=False))
        els.append(b(7, y + 1.5, 0.5, 9, y + 2.5, 1, "m", shape=False))
    return els


def wardrobe(T):
    return [b(1, 0, 1, 15, 31, 15, "p"), b(0.5, 31, 0.5, 15.5, 32, 15.5, "s"),
            b(2, 1, 0.5, 7.8, 30, 1, "s", shape=False), b(8.2, 1, 0.5, 14, 30, 1, "s", shape=False),
            b(6.5, 14, 0, 7.5, 18, 0.5, "m", shape=False), b(8.5, 14, 0, 9.5, 18, 0.5, "m", shape=False)]


def counter(T):
    return [b(0, 0, 1, 16, 14, 16, "p"), b(0, 14, 0, 16, 16, 16, "c"), b(1, 1, 0.5, 15, 13, 1, "s", shape=False),
            b(7, 9, 0, 9, 10, 0.5, "m", shape=False)]


def chabudai(T):
    return [b(1, 6, 1, 15, 8, 15, "p"), b(3, 0, 3, 5, 6, 5, "s"), b(11, 0, 3, 13, 6, 5, "s"), b(3, 0, 11, 5, 6, 13, "s"),
            b(11, 0, 11, 13, 6, 13, "s"), b(2, 5, 2, 14, 6, 14, "s", shape=False)]


WOOD_FURNITURE = [
    # id, 日本語, 英語, 作り方, 種類, オプション, レシピ
    ("chair", "の椅子", " Chair", chair, "seat", dict(seat=10), (["P  ", "PPP", "S S"], {"P": "P", "S": "minecraft:stick"}), 2),
    ("stool", "のスツール", " Stool", stool, "seat", dict(seat=11), (["HHH", "S S"], {"H": "H", "S": "minecraft:stick"}), 2),
    ("bench", "のベンチ", " Bench", bench, "seat", dict(seat=9), (["HHH", "P P"], {"H": "H", "P": "P"}), 2),
    ("table", "のテーブル", " Table", table, "basic", {}, (["HHH", "S S", "S S"], {"H": "H", "S": "minecraft:stick"}), 1),
    ("coffee_table", "のローテーブル", " Coffee Table", coffee_table, "basic", {}, (["HHH", "S S"], {"H": "H", "S": "L"}), 1),
    ("desk", "の机", " Desk", desk, "storage", dict(rows=1), (["HHH", "PCS"], {"H": "H", "P": "P", "C": "minecraft:chest", "S": "minecraft:stick"}), 1),
    ("shelf", "の壁の棚", " Wall Shelf", shelf, "basic", dict(wall=True), (["PPP", " S "], {"P": "H", "S": "minecraft:stick"}), 2),
    ("cabinet", "のタンス", " Cabinet", cabinet, "storage", dict(rows=3), (["PPP", "PCP", "PPP"], {"P": "P", "C": "minecraft:chest"}), 1),
    ("wardrobe", "のクローゼット", " Wardrobe", wardrobe, "storage", dict(rows=6, tall=True), (["PPP", "PCP", "PCP"], {"P": "P", "C": "minecraft:chest"}), 1),
    ("counter", "のキッチンカウンター", " Kitchen Counter", counter, "storage", dict(rows=2), (["SSS", "PCP", "PPP"], {"S": "minecraft:smooth_stone_slab", "P": "P", "C": "minecraft:chest"}), 1),
    ("chabudai", "のちゃぶ台", " Low Table (Chabudai)", chabudai, "basic", dict(tab="wa"), (["HHH", " L "], {"H": "H", "L": "L"}), 1),
]

for w, wja, wen in WOODS:
    T = wood_tex(w)
    T["m"] = "minecraft:block/iron_block"
    T["c"] = "minecraft:block/smooth_stone"
    items = wood_items(w)
    for fid, ja, en, fn, kind, opt, (pat, keys), cnt in WOOD_FURNITURE:
        k = {kk: items.get(v, v) for kk, v in keys.items()}
        add(F(f"{w}_{fid}", wja + ja, wen + en, kind, fn(T), {kk: T[kk] for kk in ("p", "l", "s", "m", "c")},
              recipe=(pat, k), count=cnt, **opt))

# ------------------------------------------------------------ 色の家具（16色）


def sofa():
    return [b(0, 0, 1, 2, 2, 3, "d"), b(14, 0, 1, 16, 2, 3, "d"), b(0, 0, 13, 2, 2, 15, "d"), b(14, 0, 13, 16, 2, 15, "d"),
            b(0, 2, 1, 16, 7, 15, "w"), b(0, 7, 11, 16, 16, 15, "w", shape=False), b(0, 7, 1, 2, 11, 11, "w"), b(14, 7, 1, 16, 11, 11, "w"),
            b(2, 7, 2, 14, 9, 11, "w")]


def curtain():
    return [b(0, 15, 14, 16, 16, 15, "d", shape=False), b(0, 0, 14.5, 16, 15, 15.5, "w")]


def curtain_open():
    return [b(0, 15, 14, 16, 16, 15, "d", shape=False), b(0, 0, 13.5, 3, 15, 16, "w"), b(13, 0, 13.5, 16, 15, 16, "w")]


def zabuton():
    return [b(2, 0, 2, 14, 2, 14, "w"), b(7, 2, 7, 9, 2.3, 9, "d", shape=False)]


def noren():
    return [b(0, 15, 7, 16, 16, 9, "d"), b(0.5, 5, 7.6, 7.7, 15, 8.4, "w"), b(8.3, 5, 7.6, 15.5, 15, 8.4, "w")]


for c, cja, cen in COLORS:
    wool = f"minecraft:block/{c}_wool"
    dye = f"minecraft:{c}_dye"
    add(F(f"{c}_sofa", cja + "のソファ", cen + " Sofa", "seat", sofa(), {"w": wool, "d": "minecraft:block/dark_oak_planks"}, seat=8,
          sound="wool", recipe=(["W  ", "WWW", "PPP"], {"W": f"minecraft:{c}_wool", "P": "#minecraft:planks"}), count=1))
    add(F(f"{c}_curtain", cja + "のカーテン", cen + " Curtain", "curtain", curtain(), {"w": wool, "d": "minecraft:block/dark_oak_planks"},
          open_els=curtain_open(), wall=True, sound="wool",
          recipe=(["SSS", "W W", "W W"], {"S": "minecraft:stick", "W": f"minecraft:{c}_wool"}), count=3))
    add(F(f"{c}_zabuton", cja + "の座布団", cen + " Zabuton Cushion", "seat", zabuton(), {"w": wool, "d": "minecraft:block/" + ("red" if c != "red" else "yellow") + "_wool"},
          seat=2, sound="wool", tab="wa", recipe=(["C", "W"], {"C": f"minecraft:{c}_carpet", "W": f"minecraft:{c}_wool"}), count=2))
    add(F(f"{c}_noren", cja + "ののれん", cen + " Noren Curtain", "basic", noren(), {"w": wool, "d": "minecraft:block/stripped_dark_oak_log"},
          sound="wool", tab="wa", passable=True,
          recipe=(["SSS", "W W"], {"S": "minecraft:stick", "W": f"minecraft:{c}_wool"}), count=2))

# ------------------------------------------------------------ 洋風の1つずつの家具
IRON = "minecraft:block/iron_block"
WHITE = "minecraft:block/white_concrete"
QUARTZ = "minecraft:block/quartz_block_side"
FIRE = "minecraft:block/campfire_fire"

add(F("fridge", "冷蔵庫", "Fridge", "storage", [
    b(1, 0, 2, 15, 32, 15, "w"), b(1.5, 0.5, 1, 14.5, 19.5, 2, "w", shape=False), b(1.5, 20.5, 1, 14.5, 31.5, 2, "w", shape=False),
    b(12, 12, 0, 13, 18, 1, "m", shape=False), b(12, 22, 0, 13, 27, 1, "m", shape=False)],
    {"w": WHITE, "m": IRON}, tall=True, rows=4, sound="metal", tool="pickaxe",
    recipe=(["III", "ICI", "IRI"], {"I": "minecraft:iron_ingot", "C": "minecraft:chest", "R": "minecraft:snowball"})))
add(F("stove", "コンロ", "Stove", "lamp", [
    b(0, 0, 1, 16, 14, 16, "k"), b(0, 14, 0, 16, 15, 16, "m"), b(2, 15, 2, 6, 15.5, 6, "k", shape=False), b(10, 15, 2, 14, 15.5, 6, "k", shape=False),
    b(2, 15, 10, 6, 15.5, 14, "k", shape=False), b(10, 15, 10, 14, 15.5, 14, "k", shape=False), b(2, 4, 0.5, 14, 11, 1, "g", shape=False),
    b(3, 12, 0, 4, 13, 0.5, "m", shape=False), b(6, 12, 0, 7, 13, 0.5, "m", shape=False), b(9, 12, 0, 10, 13, 0.5, "m", shape=False), b(12, 12, 0, 13, 13, 0.5, "m", shape=False)],
    {"k": "minecraft:block/black_concrete", "m": IRON, "g": "minecraft:block/tinted_glass"},
    on=lambda: cross(2, 15, 6, 18, "f", z=4) + cross(10, 15, 14, 18, "f", z=12), particles="flame", light=10, sound="metal", tool="pickaxe",
    recipe=(["III", "IFI", "III"], {"I": "minecraft:iron_ingot", "F": "minecraft:furnace"})))
add(F("sink", "シンク", "Sink", "sink", [
    b(0, 0, 1, 16, 12, 16, "p"), b(0, 12, 0, 16, 14, 16, "m"), b(0, 14, 0, 2, 16, 16, "m"), b(14, 14, 0, 16, 16, 16, "m"),
    b(2, 14, 0, 14, 16, 2, "m"), b(2, 14, 14, 14, 16, 16, "m"), b(7, 16, 13, 9, 21, 15, "m", shape=False), b(7, 19, 9, 9, 21, 13, "m", shape=False),
    b(2, 12.5, 2, 14, 13, 14, "q", shape=False)],
    {"p": "minecraft:block/oak_planks", "m": IRON, "q": "minecraft:block/water_still"}, sound="metal", tool="pickaxe",
    recipe=(["I I", "IWI", "PPP"], {"I": "minecraft:iron_ingot", "W": "minecraft:water_bucket", "P": "#minecraft:planks"})))
add(F("bathtub", "お風呂", "Bathtub", "seat", [
    b(0, 0, 0, 16, 2, 16, "q"), b(0, 2, 0, 16, 10, 1.5, "q"), b(0, 2, 14.5, 16, 10, 16, "q"), b(0, 2, 1.5, 1.5, 10, 14.5, "q"),
    b(14.5, 2, 1.5, 16, 10, 14.5, "q"), b(1.5, 7, 1.5, 14.5, 7.5, 14.5, "a", shape=False)],
    {"q": QUARTZ, "a": "minecraft:block/water_still"}, seat=3, sound="stone", tool="pickaxe",
    recipe=(["Q Q", "QQQ"], {"Q": "minecraft:quartz_block"})))
add(F("toilet", "トイレ", "Toilet", "seat", [
    b(5, 0, 3, 11, 6, 11, "q"), b(3, 6, 1, 13, 8, 12, "q"), b(3, 8, 1, 13, 8.5, 12, "w", shape=False), b(3, 6, 12, 13, 18, 16, "q", shape=False),
    b(3, 6, 12, 13, 14, 16, "q"), b(11, 15, 11.5, 12, 16, 12, "m", shape=False)],
    {"q": "minecraft:block/white_terracotta", "w": WHITE, "m": IRON}, seat=8, sound="stone", tool="pickaxe",
    recipe=(["Q  ", "QQQ", " Q "], {"Q": "minecraft:white_terracotta"})))
add(F("table_lamp", "テーブルランプ", "Table Lamp", "lamp", [
    b(5, 0, 5, 11, 1, 11, "m"), b(7.5, 1, 7.5, 8.5, 8, 8.5, "m"), b(4, 8, 4, 12, 14, 12, "g")],
    {"m": "minecraft:block/gold_block", "g": "jsn_furniture:block/lamp_shade"}, light=14, sound="glass", tool="pickaxe",
    recipe=(["WWW", "WTW", " G "], {"W": "minecraft:white_wool", "T": "minecraft:torch", "G": "minecraft:gold_ingot"})))
add(F("floor_lamp", "フロアランプ", "Floor Lamp", "lamp", [
    b(4, 0, 4, 12, 1, 12, "m"), b(7.5, 1, 7.5, 8.5, 24, 8.5, "m"), b(3, 22, 3, 13, 31, 13, "g")],
    {"m": "minecraft:block/black_concrete", "g": "jsn_furniture:block/lamp_shade"}, tall=True, light=15, sound="glass", tool="pickaxe",
    recipe=(["WWW", "WTW", " S "], {"W": "minecraft:white_wool", "T": "minecraft:torch", "S": "minecraft:iron_bars"})))
add(F("chandelier", "シャンデリア", "Chandelier", "lamp", [
    b(7.5, 10, 7.5, 8.5, 16, 8.5, "m"), b(2, 8, 7.5, 14, 9, 8.5, "m"), b(7.5, 8, 2, 8.5, 9, 14, "m"), b(6, 6, 6, 10, 10, 10, "m"),
    b(1.5, 9, 7, 3, 12, 8.5, "g"), b(13, 9, 7, 14.5, 12, 8.5, "g"), b(7, 9, 1.5, 8.5, 12, 3, "g"), b(7, 9, 13, 8.5, 12, 14.5, "g")],
    {"m": "minecraft:block/gold_block", "g": "jsn_furniture:block/candle_light"}, light=15, sound="metal", tool="pickaxe", hanging=True,
    recipe=(["GCG", "TGT", " T "], {"G": "minecraft:gold_ingot", "C": "minecraft:chain", "T": "minecraft:torch"})))
add(F("ceiling_light", "天井ライト", "Ceiling Light", "lamp", [
    b(3, 14, 3, 13, 16, 13, "m"), b(4, 13, 4, 12, 14, 12, "g")],
    {"m": WHITE, "g": "jsn_furniture:block/lamp_shade"}, light=15, sound="glass", tool="pickaxe", hanging=True,
    recipe=(["III", "GGG"], {"I": "minecraft:iron_ingot", "G": "minecraft:glowstone_dust"}), count=2))
add(F("wall_clock", "壁かけ時計", "Wall Clock", "basic", [b(3, 3, 15, 13, 13, 16, "c"), b(2.5, 2.5, 15.5, 13.5, 13.5, 16, "d")],
      {"c": "jsn_furniture:block/clock_face", "d": "minecraft:block/dark_oak_planks"}, wall=True, sound="wood",
      recipe=(["PPP", "PCP", "PPP"], {"P": "minecraft:stick", "C": "minecraft:clock"})))
add(F("mirror", "鏡", "Mirror", "basic", [b(2, 0, 15, 14, 16, 16, "f"), b(3, 1, 14.6, 13, 15, 15, "g", shape=False)],
      {"f": "minecraft:block/gold_block", "g": "jsn_furniture:block/mirror"}, wall=True, sound="glass", tool="pickaxe",
      recipe=(["GSG", "GSG", "GSG"], {"G": "minecraft:gold_nugget", "S": "minecraft:glass_pane"})))
add(F("house_plant", "大きな観葉植物", "Big House Plant", "basic", [
    b(4, 0, 4, 12, 6, 12, "t"), b(5, 6, 5, 11, 6.5, 11, "d", shape=False), b(7, 6, 7, 9, 14, 9, "l", shape=False),
    b(3, 10, 3, 13, 18, 13, "f", shape=False), b(5, 17, 5, 11, 22, 11, "f", shape=False)],
    {"t": "minecraft:block/terracotta", "d": "minecraft:block/dirt", "l": "minecraft:block/oak_log", "f": "minecraft:block/azalea_leaves"},
    sound="grass", recipe=(["L", "S", "T"], {"L": "minecraft:azalea_leaves", "S": "minecraft:stick", "T": "minecraft:terracotta"})))
add(F("display_case", "ショーケース", "Display Case", "display", [
    b(1, 0, 1, 15, 4, 15, "p"), b(1, 15, 1, 15, 16, 15, "p"), b(1.5, 4, 1.5, 14.5, 15, 14.5, "g")],
    {"p": "minecraft:block/dark_oak_planks", "g": "jsn_furniture:block/case_glass"}, sound="glass",
    recipe=(["GGG", "G G", "PPP"], {"G": "minecraft:glass", "P": "#minecraft:planks"})))
add(F("cash_register", "レジ", "Cash Register", "basic", [
    b(2, 0, 3, 14, 5, 14, "k"), b(3, 5, 6, 13, 9, 13, "k"), b(4, 9, 9, 12, 13, 12, "s"), b(3, 5, 3, 13, 6, 6, "b", shape=False)],
    {"k": "minecraft:block/gray_concrete", "s": "jsn_furniture:block/register_screen", "b": "jsn_furniture:block/register_keys"},
    sound="metal", tool="pickaxe", recipe=(["IGI", "IRI", "III"], {"I": "minecraft:iron_ingot", "G": "minecraft:glass_pane", "R": "minecraft:redstone"})))
add(F("signboard", "立て看板", "Signboard", "basic", [
    b(1, 0, 6, 15, 16, 7, "s"), b(1, 0, 9, 15, 16, 10, "s"), b(1, 15, 6, 15, 16, 10, "p", shape=False)],
    {"s": "jsn_furniture:block/signboard", "p": "minecraft:block/dark_oak_planks"}, sound="wood",
    recipe=(["PPP", "PBP", "S S"], {"P": "#minecraft:planks", "B": "minecraft:black_dye", "S": "minecraft:stick"})))
add(F("street_lamp", "街灯", "Street Lamp", "lamp", [
    b(6, 0, 6, 10, 2, 10, "m"), b(7, 2, 7, 9, 26, 9, "m"), b(5, 26, 5, 11, 27, 11, "m"), b(5.5, 27, 5.5, 10.5, 31, 10.5, "g"), b(6, 31, 6, 10, 32, 10, "m")],
    {"m": "minecraft:block/black_concrete", "g": "jsn_furniture:block/lamp_glass"}, tall=True, light=15, sound="metal", tool="pickaxe",
    recipe=(["IGI", " I ", " I "], {"I": "minecraft:iron_ingot", "G": "minecraft:glowstone"})))
add(F("parasol", "パラソル", "Parasol", "basic", [
    b(7.5, 0, 7.5, 8.5, 28, 8.5, "m"), b(4, 0, 4, 12, 1, 12, "m"),
    b(-6, 26, -6, 22, 27, 22, "c", shape=False), b(-2, 27, -2, 18, 28, 18, "c", shape=False), b(3, 28, 3, 13, 29, 13, "c", shape=False)],
    {"m": WHITE, "c": "jsn_furniture:block/parasol"}, tall=True, sound="wool",
    recipe=(["WRW", " S ", " S "], {"W": "minecraft:white_wool", "R": "minecraft:red_wool", "S": "minecraft:stick"})))

# ------------------------------------------------------------ 和風の1つずつの家具
add(F("kotatsu", "こたつ", "Kotatsu", "seat", [
    b(0, 0, 0, 16, 6, 16, "f"), b(-1, 6, -1, 17, 7, 17, "f", shape=False), b(0, 7, 0, 16, 8, 16, "t"), b(-0.5, 7, -0.5, 16.5, 8, 16.5, "t", shape=False)],
    {"f": "jsn_furniture:block/kotatsu_futon", "t": "minecraft:block/spruce_planks"}, seat=4, tab="wa", sound="wool",
    recipe=(["HHH", "WWW", "S S"], {"H": "minecraft:spruce_slab", "W": "minecraft:red_wool", "S": "minecraft:stick"})))
add(F("sudare", "すだれ", "Sudare Blind", "curtain", [b(0, 15, 14, 16, 16, 15, "r", shape=False), b(0, 0, 14.6, 16, 15, 15.4, "s")],
      {"s": "jsn_furniture:block/sudare", "r": "minecraft:block/stripped_bamboo_block"}, wall=True, tab="wa", sound="bamboo",
      open_els=[b(0, 15, 14, 16, 16, 15, "r", shape=False), b(0, 12, 13.5, 16, 15, 16, "r")],
      recipe=(["SSS", "BBB", "BBB"], {"S": "minecraft:string", "B": "minecraft:bamboo"}), count=3))
add(F("andon", "行灯", "Andon Lamp", "lamp", [
    b(4, 0, 4, 12, 2, 12, "w"), b(4, 2, 4, 12, 14, 12, "g"), b(3.5, 2, 3.5, 4.5, 14, 4.5, "w", shape=False), b(11.5, 2, 3.5, 12.5, 14, 4.5, "w", shape=False),
    b(3.5, 2, 11.5, 4.5, 14, 12.5, "w", shape=False), b(11.5, 2, 11.5, 12.5, 14, 12.5, "w", shape=False), b(4, 14, 4, 12, 15, 12, "w")],
    {"w": "minecraft:block/dark_oak_planks", "g": "jsn_furniture:block/washi"}, light=12, tab="wa",
    recipe=(["SPS", "PTP", "SPS"], {"S": "minecraft:stick", "P": "minecraft:paper", "T": "minecraft:torch"})))
for col, cja, cen in (("red", "赤", "Red"), ("white", "白", "White")):
    add(F(f"chochin_{col}", f"{cja}い提灯", f"{cen} Chochin Lantern", "lamp", [
        b(7, 13, 7, 9, 16, 9, "k", shape=False), b(5, 11, 5, 11, 13, 11, "k"), b(4, 3, 4, 12, 11, 12, "g"), b(5, 1, 5, 11, 3, 11, "k")],
        {"k": "minecraft:block/black_concrete", "g": f"jsn_furniture:block/chochin_{col}"}, light=13, tab="wa", hanging=True, sound="wool",
        recipe=(["S", "P", "T"], {"S": "minecraft:string", "P": "minecraft:paper" if col == "white" else "minecraft:red_dye", "T": "minecraft:torch"}), count=1))
add(F("toro", "石灯籠", "Stone Lantern (Toro)", "lamp", [
    b(4, 0, 4, 12, 3, 12, "s"), b(6, 3, 6, 10, 14, 10, "s"), b(3, 14, 3, 13, 16, 13, "s"), b(4, 16, 4, 12, 22, 12, "s"),
    b(5, 17, 3.9, 11, 21, 12.1, "g", shape=False), b(3.9, 17, 5, 12.1, 21, 11, "g", shape=False),
    b(1, 22, 1, 15, 24, 15, "s"), b(4, 24, 4, 12, 26, 12, "s"), b(7, 26, 7, 9, 28, 9, "s")],
    {"s": "minecraft:block/stone", "g": "jsn_furniture:block/toro_window"}, tall=True, light=13, tab="wa", sound="stone", tool="pickaxe",
    recipe=(["SSS", " T ", "SSS"], {"S": "minecraft:stone_slab", "T": "minecraft:torch"})))
add(F("irori", "囲炉裏", "Irori Hearth", "lamp", [
    b(0, 0, 0, 16, 3, 16, "w"), b(2, 3, 2, 14, 3.2, 14, "a", shape=False), b(0, 3, 0, 16, 4, 2, "w"), b(0, 3, 14, 16, 4, 16, "w"),
    b(0, 3, 2, 2, 4, 14, "w"), b(14, 3, 2, 16, 4, 14, "w"), b(5, 3, 6, 11, 4, 7, "l", shape=False), b(6, 3, 9, 12, 4, 10, "l", shape=False)],
    {"w": "minecraft:block/stripped_spruce_log", "a": "jsn_furniture:block/ash", "l": "minecraft:block/oak_log"},
    on=lambda: cross(4, 3, 12, 12, "f"), particles="flame_smoke", light=13, tab="wa",
    recipe=(["LLL", "LCL", "LLL"], {"L": "minecraft:stripped_spruce_log", "C": "minecraft:campfire"})))
add(F("tatami", "畳", "Tatami", "basic", [b(0, 0, 0, 16, 16, 16, {"up": "t", "down": "s", "north": "s", "south": "s", "east": "s", "west": "s"})],
      {"t": "jsn_furniture:block/tatami", "s": "jsn_furniture:block/tatami_side"}, full=True, tab="wa", sound="grass",
      recipe=(["WWW", "HHH"], {"W": "minecraft:wheat", "H": "minecraft:hay_block"}), count=4))
add(F("tatami_half", "半畳", "Half Tatami", "basic", [b(0, 0, 0, 16, 16, 16, {"up": "t", "down": "s", "north": "s", "south": "s", "east": "s", "west": "s"})],
      {"t": "jsn_furniture:block/tatami_half", "s": "jsn_furniture:block/tatami_side"}, full=True, tab="wa", sound="grass",
      recipe=(["WW", "HH"], {"W": "minecraft:wheat", "H": "minecraft:hay_block"}), count=4))
for i, (kid, kja, ken) in enumerate((("fuji", "富士山", "Mt. Fuji"), ("koi", "鯉", "Koi"), ("wa", "和の書", "Calligraphy"))):
    add(F(f"kakejiku_{kid}", f"掛け軸（{kja}）", f"Hanging Scroll ({ken})", "basic", [
        b(4, 1, 15.5, 12, 15, 16, "p"), b(3, 15, 15, 13, 16, 16, "r"), b(3, 0, 15, 13, 1, 16, "r")],
        {"p": f"jsn_furniture:block/kakejiku_{kid}", "r": "minecraft:block/stripped_dark_oak_log"}, wall=True, tab="wa", sound="wool",
        recipe=(["S", "P", "X"], {"S": "minecraft:stick", "P": "minecraft:paper", "X": ["minecraft:snowball", "minecraft:cod", "minecraft:ink_sac"][i]})))
add(F("bonsai", "盆栽", "Bonsai", "basic", [
    b(3, 0, 5, 13, 3, 11, "t"), b(7, 3, 7, 9, 8, 9, "l", shape=False), b(5, 7, 6, 9, 8, 8, "l", shape=False),
    b(3, 8, 4, 9, 11, 10, "f", shape=False), b(8, 9, 6, 13, 12, 10, "f", shape=False), b(5, 11, 5, 10, 13, 9, "f", shape=False)],
    {"t": "minecraft:block/brown_terracotta", "l": "minecraft:block/spruce_log", "f": "minecraft:block/spruce_leaves_opaque"},
    tab="wa", sound="grass", recipe=(["L", "S", "T"], {"L": "minecraft:spruce_sapling", "S": "minecraft:stick", "T": "minecraft:brown_terracotta"})))
add(F("wagasa", "和傘", "Wagasa Umbrella", "basic", [
    b(7.5, 0, 7.5, 8.5, 26, 8.5, "s"), b(5, 0, 5, 11, 1, 11, "s"),
    b(-4, 24, -4, 20, 25, 20, "c", shape=False), b(0, 25, 0, 16, 26, 16, "c", shape=False), b(4, 26, 4, 12, 27, 12, "c", shape=False)],
    {"s": "minecraft:block/stripped_bamboo_block", "c": "jsn_furniture:block/wagasa"}, tall=True, tab="wa", sound="bamboo",
    recipe=(["PRP", " B ", " B "], {"P": "minecraft:paper", "R": "minecraft:red_dye", "B": "minecraft:bamboo"})))
add(F("saisenbako", "賽銭箱", "Offering Box", "storage", [
    b(1, 0, 3, 15, 10, 13, "w"), b(0.5, 10, 2.5, 15.5, 11, 13.5, "w"), b(2, 11, 4, 14, 11.2, 12, "s", shape=False)],
    {"w": "minecraft:block/spruce_planks", "s": "jsn_furniture:block/saisen_top"}, rows=1, tab="wa",
    recipe=(["SSS", "PCP"], {"S": "minecraft:spruce_slab", "P": "minecraft:spruce_planks", "C": "minecraft:chest"})))
TORII_R = "jsn_furniture:block/torii_red"
add(F("torii_pillar", "鳥居の柱", "Torii Pillar", "basic", [b(4, 0, 4, 12, 16, 12, "r")], {"r": TORII_R}, tab="wa",
      recipe=(["R", "L", "L"], {"R": "minecraft:red_dye", "L": "#minecraft:logs"}), count=3))
add(F("torii_kasagi", "鳥居の笠木", "Torii Top Beam", "basic", [b(0, 0, 3, 16, 6, 13, "r"), b(0, 6, 2, 16, 10, 14, "k")],
      {"r": TORII_R, "k": "minecraft:block/black_concrete"}, tab="wa",
      recipe=(["BBB", "RRR", "LLL"], {"B": "minecraft:black_dye", "R": "minecraft:red_dye", "L": "#minecraft:logs"}), count=3))
add(F("torii_nuki", "鳥居の貫", "Torii Cross Beam", "basic", [b(0, 5, 5, 16, 11, 11, "r")], {"r": TORII_R}, tab="wa",
      recipe=(["RRR", "LLL"], {"R": "minecraft:red_dye", "L": "#minecraft:logs"}), count=3))
add(F("shishi_odoshi", "鹿威し", "Shishi-odoshi", "shishi", [
    b(0, 0, 3, 16, 2, 13, "s"), b(1, 2, 5, 2, 9, 11, "b"), b(14, 2, 5, 15, 9, 11, "b"),
    b(2, 4, 6.5, 15, 7, 9.5, "b", shape=False, rot={"origin": [8, 6, 8], "axis": "z", "angle": -22.5}),
    b(0, 9, 7, 6, 11, 9, "b", shape=False)],
    {"s": "minecraft:block/cobblestone", "b": "minecraft:block/bamboo_block"}, tab="wa", sound="bamboo",
    tilt_els=[b(0, 0, 3, 16, 2, 13, "s"), b(1, 2, 5, 2, 9, 11, "b"), b(14, 2, 5, 15, 9, 11, "b"),
              b(2, 4, 6.5, 15, 7, 9.5, "b", shape=False, rot={"origin": [8, 6, 8], "axis": "z", "angle": 22.5}),
              b(0, 9, 7, 6, 11, 9, "b", shape=False)],
    recipe=(["B  ", "BBB", "CWC"], {"B": "minecraft:bamboo", "C": "minecraft:cobblestone", "W": "minecraft:water_bucket"})))

# ------------------------------------------------------------ 風鈴
FURIN = []
for c, cja, cen in COLORS:
    FURIN.append((f"furin_{c}", f"{cja}の風鈴", f"{cen} Wind Chime", "glass", f"minecraft:{c}_stained_glass_pane", "minecraft:paper", ("color", c)))
for pid, pja, pen, item in (("kingyo", "金魚", "Goldfish", "minecraft:tropical_fish"), ("asagao", "朝顔", "Morning Glory", "minecraft:cornflower"),
                            ("hanabi", "花火", "Fireworks", "minecraft:firework_rocket"), ("nami", "波", "Waves", "minecraft:prismarine_shard"),
                            ("sakura", "桜", "Sakura", "minecraft:pink_petals"), ("suika", "すいか", "Watermelon", "minecraft:melon_slice")):
    FURIN.append((f"furin_{pid}", f"{pja}の風鈴", f"{pen} Wind Chime", "glass", "minecraft:glass_pane", item, ("pattern", pid)))
FURIN.append(("furin_nanbu", "南部鉄器の風鈴", "Iron Wind Chime (Nanbu)", "iron", "minecraft:iron_ingot", "minecraft:paper", ("iron", None)))
FURIN.append(("furin_bamboo", "竹の風鈴", "Bamboo Wind Chime", "bamboo", "minecraft:bamboo", "minecraft:paper", ("bamboo", None)))
FURIN.append(("furin_ceramic", "陶器の風鈴", "Ceramic Wind Chime", "ceramic", "minecraft:white_glazed_terracotta", "minecraft:paper", ("ceramic", None)))
FURIN.append(("furin_brass", "真鍮の風鈴", "Brass Wind Chime", "brass", "minecraft:gold_ingot", "minecraft:paper", ("brass", None)))


def furin_hook():
    return [b(7.6, 14, 7.6, 8.4, 16, 8.4, "h")]


def furin_body(kind):
    # 本体は、ぶら下がり点（8, 14, 8）を中心にゆれる
    if kind == "bamboo":
        return [b(7.7, 12, 7.7, 8.3, 14, 8.3, "h"), b(5, 11, 5, 11, 12, 11, "g"),
                b(5.5, 6, 5.5, 6.7, 11, 6.7, "g"), b(9.3, 5, 5.5, 10.5, 11, 6.7, "g"), b(5.5, 7, 9.3, 6.7, 11, 10.5, "g"),
                b(9.3, 6.5, 9.3, 10.5, 11, 10.5, "g"), b(7.4, 4, 7.4, 8.6, 9, 8.6, "g"),
                b(7.8, 0, 7.95, 8.2, 4, 8.05, "h"), b(7, -6, 7.95, 9, 0, 8.05, "t")]
    return [b(7.7, 12, 7.7, 8.3, 14, 8.3, "h"), b(5.5, 11, 5.5, 10.5, 12, 10.5, "g"), b(4.5, 7, 4.5, 11.5, 11, 11.5, "g"),
            b(7.8, 3, 7.95, 8.2, 7, 8.05, "h"), b(7.3, 5.5, 7.3, 8.7, 6.5, 8.7, "h"),
            b(6.8, -5, 7.95, 9.2, 3, 8.05, "t")]


for fid, ja, en, kind, glass_item, extra_item, look in FURIN:
    tex = {"h": "minecraft:block/white_wool" if kind != "iron" else "minecraft:block/black_wool",
           "g": f"jsn_furniture:block/{fid}", "t": "jsn_furniture:block/tanzaku"}
    add(F(fid, ja, en, "furin", furin_hook(), tex, body=furin_body(kind), furin=kind if kind != "brass" else "brass",
          tab="wa", hanging=True, sound="glass" if kind == "glass" else ("bamboo" if kind == "bamboo" else "metal"),
          tool="axe" if kind == "bamboo" else "pickaxe",
          recipe=(["S", "G", "X"], {"S": "minecraft:string", "G": glass_item, "X": extra_item})))

# ============================================================ テクスチャ


def noise_fill(im, base, amt=8, seed=0):
    rnd = random.Random(seed)
    for y in range(im.height):
        for x in range(im.width):
            v = rnd.randint(-amt, amt)
            im.putpixel((x, y), tuple(max(0, min(255, c + v)) for c in base[:3]) + (255,))


def tex_furin(fid, kind, look):
    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    lk, arg = look
    if lk == "color":
        c = hx(DYE_RGB[arg])
        base = tuple(int(v * 0.6 + 255 * 0.4) for v in c[:3]) + (200,)
        d.rectangle([0, 0, 15, 15], fill=base)
        d.line([0, 3, 15, 3], fill=shade(c, 0.8)[:3] + (230,))
        d.rectangle([2, 6, 3, 12], fill=(255, 255, 255, 170))
    elif lk == "pattern":
        d.rectangle([0, 0, 15, 15], fill=(225, 240, 250, 170))
        if arg == "kingyo":
            for (x, y) in ((3, 7), (10, 10)):
                d.ellipse([x, y, x + 3, y + 2], fill=(235, 60, 30, 255)); d.polygon([(x + 3, y + 1), (x + 5, y - 1), (x + 5, y + 3)], fill=(235, 90, 40, 255))
            d.point([(8, 4), (12, 5)], fill=(120, 180, 230, 255))
        elif arg == "asagao":
            for (x, y) in ((3, 6), (10, 9)):
                d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(70, 80, 210, 255)); d.point((x, y), fill=(255, 255, 255, 255))
            d.line([(0, 13), (5, 10), (9, 13), (15, 11)], fill=(60, 150, 60, 255))
        elif arg == "hanabi":
            d.rectangle([0, 0, 15, 15], fill=(30, 35, 80, 190))
            for (x, y, col) in ((4, 6, (255, 200, 60)), (11, 9, (255, 90, 160))):
                for a in range(8):
                    r = math.radians(a * 45)
                    d.line([x, y, x + round(math.cos(r) * 3), y + round(math.sin(r) * 3)], fill=col + (255,))
        elif arg == "nami":
            for y0 in (5, 9, 13):
                d.line([(0, y0), (3, y0 - 2), (6, y0), (9, y0 - 2), (12, y0), (15, y0 - 2)], fill=(40, 100, 200, 255))
        elif arg == "sakura":
            d.rectangle([0, 0, 15, 15], fill=(250, 230, 240, 180))
            for (x, y) in ((4, 6), (11, 8), (6, 12)):
                for a in range(5):
                    r = math.radians(a * 72 - 90)
                    d.point((x + round(math.cos(r) * 1.6), y + round(math.sin(r) * 1.6)), fill=(240, 130, 170, 255))
                d.point((x, y), fill=(250, 220, 90, 255))
        elif arg == "suika":
            d.rectangle([0, 0, 15, 15], fill=(80, 160, 60, 210))
            for x0 in (2, 7, 12):
                d.line([(x0, 0), (x0 + 1, 5), (x0, 10), (x0 + 1, 15)], fill=(30, 80, 30, 255))
        d.line([0, 3, 15, 3], fill=(160, 190, 210, 230))
    elif lk == "iron":
        noise_fill(im, (55, 55, 60), 6, hash(fid) & 255)
        for y in range(4, 16, 3):
            for x in range(1 + (y % 2), 16, 3):
                im.putpixel((x, y), (75, 75, 80, 255))
    elif lk == "bamboo":
        noise_fill(im, (170, 190, 90), 10, 3)
        for y in (4, 11):
            d.line([0, y, 15, y], fill=(120, 140, 60, 255))
    elif lk == "ceramic":
        d.rectangle([0, 0, 15, 15], fill=(240, 240, 235, 255))
        d.line([0, 4, 15, 4], fill=(40, 70, 160, 255)); d.line([0, 12, 15, 12], fill=(40, 70, 160, 255))
        for x in (2, 7, 12):
            d.ellipse([x, 6, x + 3, 9], outline=(40, 70, 160, 255))
    elif lk == "brass":
        noise_fill(im, (200, 160, 70), 10, 5)
        d.line([0, 4, 15, 4], fill=(240, 210, 120, 255))
    save(im, f"block/{fid}")


def make_textures():
    for fid, ja, en, kind, gi, xi, look in FURIN:
        tex_furin(fid, kind, look)
    # 短冊
    im = Image.new("RGBA", (16, 16), (250, 245, 225, 255)); d = ImageDraw.Draw(im)
    d.line([7, 3, 8, 6], fill=(30, 30, 30, 255)); d.line([6, 8, 9, 8], fill=(30, 30, 30, 255)); d.line([8, 9, 7, 12], fill=(30, 30, 30, 255))
    save(im, "block/tanzaku")
    # ランプのかさ
    im = Image.new("RGBA", (16, 16)); noise_fill(im, (245, 230, 190), 5, 1); d = ImageDraw.Draw(im)
    d.line([0, 0, 15, 0], fill=(200, 180, 140, 255)); d.line([0, 15, 15, 15], fill=(200, 180, 140, 255)); save(im, "block/lamp_shade")
    im = Image.new("RGBA", (16, 16), (255, 230, 150, 255)); ImageDraw.Draw(im).rectangle([5, 4, 10, 13], fill=(255, 250, 220, 255)); save(im, "block/candle_light")
    im = Image.new("RGBA", (16, 16), (250, 240, 200, 255)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 15, 15], outline=(40, 40, 40, 255)); d.line([8, 0, 8, 15], fill=(40, 40, 40, 255)); d.line([0, 8, 15, 8], fill=(40, 40, 40, 255))
    save(im, "block/lamp_glass")
    # 時計
    im = Image.new("RGBA", (16, 16), (245, 240, 225, 255)); d = ImageDraw.Draw(im)
    d.ellipse([0, 0, 15, 15], outline=(60, 40, 20, 255))
    for a in range(12):
        r = math.radians(a * 30)
        d.point((round(7.5 + math.cos(r) * 6), round(7.5 + math.sin(r) * 6)), fill=(30, 30, 30, 255))
    d.line([8, 8, 8, 3], fill=(20, 20, 20, 255)); d.line([8, 8, 11, 9], fill=(20, 20, 20, 255)); save(im, "block/clock_face")
    # 鏡・ガラス
    im = Image.new("RGBA", (16, 16), (190, 215, 230, 255)); d = ImageDraw.Draw(im)
    for i in range(3):
        d.line([2 + i * 4, 15, 9 + i * 4, 0], fill=(235, 245, 250, 255))
    save(im, "block/mirror")
    im = Image.new("RGBA", (16, 16), (220, 240, 250, 60)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 15, 15], outline=(240, 250, 255, 200)); d.line([2, 13, 5, 10], fill=(255, 255, 255, 200)); save(im, "block/case_glass")
    # レジ
    im = Image.new("RGBA", (16, 16), (30, 60, 40, 255)); d = ImageDraw.Draw(im); d.rectangle([1, 1, 14, 14], fill=(60, 200, 110, 255))
    d.text((2, 3), "123", fill=(20, 60, 30, 255)); save(im, "block/register_screen")
    im = Image.new("RGBA", (16, 16), (90, 90, 95, 255)); d = ImageDraw.Draw(im)
    for y in range(1, 16, 4):
        for x in range(1, 16, 4):
            d.rectangle([x, y, x + 2, y + 2], fill=(220, 220, 220, 255))
    save(im, "block/register_keys")
    # 看板（黒板）
    im = Image.new("RGBA", (16, 16), (40, 60, 45, 255)); d = ImageDraw.Draw(im); d.rectangle([0, 0, 15, 15], outline=(110, 80, 50, 255))
    d.line([3, 4, 12, 4], fill=(230, 230, 220, 255)); d.line([3, 8, 10, 8], fill=(230, 230, 220, 255)); d.line([3, 11, 11, 11], fill=(230, 230, 220, 255))
    save(im, "block/signboard")
    # パラソル・和傘
    im = Image.new("RGBA", (16, 16)); d = ImageDraw.Draw(im)
    for x in range(16):
        d.line([x, 0, x, 15], fill=(220, 50, 50, 255) if (x // 4) % 2 == 0 else (245, 245, 245, 255))
    save(im, "block/parasol")
    im = Image.new("RGBA", (16, 16)); noise_fill(im, (190, 30, 40), 8, 7); d = ImageDraw.Draw(im)
    for a in range(8):
        r = math.radians(a * 45)
        d.line([8, 8, 8 + round(math.cos(r) * 9), 8 + round(math.sin(r) * 9)], fill=(150, 20, 30, 255))
    save(im, "block/wagasa")
    # こたつの布団
    im = Image.new("RGBA", (16, 16)); noise_fill(im, (170, 40, 50), 6, 9); d = ImageDraw.Draw(im)
    for x in range(0, 16, 4):
        d.line([x, 0, x, 15], fill=(200, 160, 60, 255))
    save(im, "block/kotatsu_futon")
    # すだれ
    im = Image.new("RGBA", (16, 16), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    for y in range(0, 16, 2):
        d.line([0, y, 15, y], fill=(200, 180, 110, 255))
    d.line([4, 0, 4, 15], fill=(120, 90, 50, 255)); d.line([11, 0, 11, 15], fill=(120, 90, 50, 255)); save(im, "block/sudare")
    # 和紙・提灯
    im = Image.new("RGBA", (16, 16)); noise_fill(im, (248, 238, 210), 4, 11); d = ImageDraw.Draw(im)
    d.line([0, 5, 15, 5], fill=(200, 185, 150, 255)); d.line([0, 10, 15, 10], fill=(200, 185, 150, 255)); save(im, "block/washi")
    for col, rgb in (("red", (205, 40, 35)), ("white", (245, 240, 225))):
        im = Image.new("RGBA", (16, 16)); noise_fill(im, rgb, 5, 13); d = ImageDraw.Draw(im)
        for y in range(1, 16, 3):
            d.line([0, y, 15, y], fill=shade(rgb, 0.8))
        if col == "white":
            d.text((4, 3), "祭", fill=(30, 30, 30, 255))
        save(im, f"block/chochin_{col}")
    im = Image.new("RGBA", (16, 16), (255, 200, 110, 255)); save(im, "block/toro_window")
    im = Image.new("RGBA", (16, 16)); noise_fill(im, (110, 105, 100), 14, 17); save(im, "block/ash")
    # 畳
    for name, half in (("tatami", False), ("tatami_half", True)):
        im = Image.new("RGBA", (16, 16)); noise_fill(im, (186, 190, 120), 6, 19); d = ImageDraw.Draw(im)
        for y in range(0, 16, 2):
            d.line([0, y, 15, y], fill=(170, 175, 105, 255))
        d.rectangle([0, 0, 15, 1], fill=(60, 70, 50, 255)); d.rectangle([0, 14, 15, 15], fill=(60, 70, 50, 255))
        if half:
            d.rectangle([0, 0, 1, 15], fill=(60, 70, 50, 255)); d.rectangle([14, 0, 15, 15], fill=(60, 70, 50, 255))
        save(im, f"block/{name}")
    im = Image.new("RGBA", (16, 16)); noise_fill(im, (160, 165, 105), 6, 21); save(im, "block/tatami_side")
    # 掛け軸
    for kid in ("fuji", "koi", "wa"):
        im = Image.new("RGBA", (16, 16), (245, 238, 215, 255)); d = ImageDraw.Draw(im)
        d.rectangle([0, 0, 15, 15], outline=(140, 110, 70, 255))
        if kid == "fuji":
            d.polygon([(2, 12), (8, 4), (14, 12)], fill=(80, 110, 170, 255)); d.polygon([(6, 6.5), (8, 4), (10, 6.5)], fill=(255, 255, 255, 255))
            d.ellipse([10, 2, 13, 5], fill=(210, 50, 40, 255))
        elif kid == "koi":
            d.ellipse([4, 4, 12, 8], fill=(230, 90, 40, 255)); d.polygon([(12, 6), (14, 4), (14, 8)], fill=(230, 90, 40, 255))
            d.ellipse([3, 10, 10, 13], fill=(240, 240, 240, 255)); d.point((5, 11), fill=(220, 50, 40, 255))
        else:
            d.line([8, 2, 8, 13], fill=(20, 20, 20, 255), width=2); d.line([4, 5, 12, 5], fill=(20, 20, 20, 255)); d.line([5, 10, 11, 12], fill=(20, 20, 20, 255))
            d.rectangle([11, 13, 13, 14], fill=(200, 40, 40, 255))
        save(im, f"block/kakejiku_{kid}")
    im = Image.new("RGBA", (16, 16)); noise_fill(im, (120, 80, 45), 8, 23); d = ImageDraw.Draw(im)
    for x in range(1, 16, 2):
        d.line([x, 0, x, 15], fill=(50, 30, 15, 255))
    save(im, "block/saisen_top")
    im = Image.new("RGBA", (16, 16)); noise_fill(im, (200, 45, 35), 6, 25); save(im, "block/torii_red")
    # 障子・ふすま（ドア）
    for half in ("bottom", "top"):
        im = Image.new("RGBA", (16, 16), (250, 246, 232, 255)); d = ImageDraw.Draw(im)
        frame = (150, 110, 70, 255)
        d.rectangle([0, 0, 15, 15], outline=frame); d.rectangle([0, 0, 1, 15], fill=frame); d.rectangle([14, 0, 15, 15], fill=frame)
        for x in (5, 10):
            d.line([x, 0, x, 15], fill=frame)
        for y in (4, 8, 12):
            d.line([0, y, 15, y], fill=frame)
        if half == "bottom":
            d.rectangle([0, 12, 15, 15], fill=frame)
        save(im, f"block/shoji_{half}")
        im = Image.new("RGBA", (16, 16)); noise_fill(im, (225, 215, 185), 4, 27 if half == "top" else 29); d = ImageDraw.Draw(im)
        d.rectangle([0, 0, 15, 15], outline=(40, 30, 25, 255)); d.rectangle([0, 0, 0, 15], fill=(40, 30, 25, 255)); d.rectangle([15, 0, 15, 15], fill=(40, 30, 25, 255))
        if half == "top":
            d.line([(1, 12), (5, 8), (9, 10), (14, 5)], fill=(90, 120, 80, 255)); d.ellipse([10, 2, 13, 5], fill=(220, 190, 90, 255))
        else:
            d.ellipse([11, 6, 13, 8], fill=(60, 50, 40, 255))
            d.line([(1, 3), (5, 5), (8, 3), (14, 6)], fill=(90, 120, 80, 255))
        save(im, f"block/fusuma_{half}")
    for name in ("shoji", "fusuma"):
        top = Image.open(f"{A}/textures/block/{name}_top.png"); bot = Image.open(f"{A}/textures/block/{name}_bottom.png")
        im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        im.paste(top.resize((8, 8), Image.NEAREST), (4, 0)); im.paste(bot.resize((8, 8), Image.NEAREST), (4, 8))
        save(im, f"item/{name}")
    # ベッドの布
    im = Image.new("RGBA", (16, 16)); noise_fill(im, (240, 240, 245), 3, 31); save(im, "block/bed_sheet")
    im = Image.new("RGBA", (16, 16)); noise_fill(im, (70, 100, 170), 5, 33); d = ImageDraw.Draw(im)
    for x in range(0, 16, 4):
        for y in range(0, 16, 4):
            d.point((x + 1, y + 1), fill=(240, 240, 250, 255))
    save(im, "block/futon_cover")


# ============================================================ 出力

BLOCKSTATE_Y = {"north": 0, "east": 90, "south": 180, "west": 270}


def boxes(els):
    out = []
    for e in els:
        if not e.shape:
            continue
        x1, y1, z1 = e.f
        x2, y2, z2 = e.t
        out.append([max(0, min(16, x1)), max(0, y1), max(0, min(16, z1)), max(0, min(16, x2)), min(32, y2), max(0, min(16, z2))])
    return out


def variants(fur, model_for):
    """facing（と lit/open/half/tilt）ごとのモデル"""
    v = {}
    props = []
    if fur.tall:
        props.append(("half", ["lower", "upper"]))
    if fur.kind in ("lamp",):
        props.append(("lit", ["false", "true"]))
    if fur.kind == "curtain":
        props.append(("open", ["false", "true"]))
    if fur.kind == "shishi":
        props.append(("tilt", ["false", "true"]))

    def rec(i, cur):
        if i == len(props):
            for f, y in BLOCKSTATE_Y.items():
                key = ",".join([f"facing={f}"] + [f"{k}={val}" for k, val in cur])
                m = {"model": model_for(dict(cur))}
                if y:
                    m["y"] = y
                v[key] = m
            return
        k, vals = props[i]
        for val in vals:
            rec(i + 1, cur + [(k, val)])
    rec(0, [])
    return v


def write_furniture(fur):
    tex = dict(fur.tex)
    if fur.on or fur.particles:
        tex["f"] = FIRE
    base_els = fur.els
    models = {}

    rt = "minecraft:translucent" if fur.kind in ("display", "furin") else "minecraft:cutout"

    def emit(name, els, lo=None, hi=None, dy=0):
        wj(f"{A}/models/block/{name}.json", model_json(els, tex, dy=dy, lo=lo, hi=hi, render_type=rt))
        return f"{NS}:block/{name}"

    sets = {"": base_els}
    if fur.on:
        sets["_on"] = base_els + fur.on()
    if fur.open_els:
        sets["_open"] = fur.open_els
    if fur.tilt_els:
        sets["_tilt"] = fur.tilt_els
    for suffix, els in sets.items():
        if fur.tall:
            models[suffix + "_lower"] = emit(f"{fur.id}{suffix}_lower", els, lo=0, hi=16)
            models[suffix + "_upper"] = emit(f"{fur.id}{suffix}_upper", els, lo=16, hi=32, dy=-16)
        else:
            models[suffix] = emit(f"{fur.id}{suffix}", els)

    def model_for(st):
        suffix = ""
        if st.get("lit") == "true" and fur.on:
            suffix = "_on"
        if st.get("open") == "true":
            suffix = "_open"
        if st.get("tilt") == "true":
            suffix = "_tilt"
        if fur.tall:
            suffix += "_" + st["half"]
        return models[suffix]

    wj(f"{A}/blockstates/{fur.id}.json", {"variants": variants(fur, model_for)})
    # アイテムの見た目：全体
    item_els = base_els + (fur.body or [])
    wj(f"{A}/models/item/{fur.id}.json", model_json(item_els, tex, display=TALL_DISPLAY if fur.tall or fur.id in ("parasol",) else None, render_type=rt))
    if fur.body:
        wj(f"{A}/models/block/{fur.id}_body.json", model_json(fur.body, tex, render_type=rt))
    # ドロップ
    cond = [{"condition": "minecraft:block_state_property", "block": f"{NS}:{fur.id}", "properties": {"half": "lower"}}] if fur.tall else []
    pool = {"rolls": 1, "entries": [{"type": "minecraft:item", "name": f"{NS}:{fur.id}"}], "conditions": [{"condition": "minecraft:survives_explosion"}] + cond}
    wj(f"{D}/loot_table/blocks/{fur.id}.json", {"type": "minecraft:block", "pools": [pool]})


# ---------------- ベッド（木の種類ごと＋布団）

BEDS = []


def bed_parts(T, futon=False):
    if futon:
        head = [b(1, 0, 0, 15, 3, 16, "w"), b(1, 3, 1, 15, 4, 16, "c"), b(3, 3, 1, 13, 5, 6, "w")]
        foot = [b(1, 0, 0, 15, 3, 16, "w"), b(1, 3, 0, 15, 4, 15, "c")]
        return head, foot
    head = [b(0, 0, 0, 2, 16, 2, "l"), b(14, 0, 0, 16, 16, 2, "l"), b(2, 3, 0, 14, 14, 1.5, "p"),
            b(0, 3, 1.5, 16, 6, 16, "p"), b(1, 6, 1.5, 15, 9, 16, "w"), b(3, 9, 2.5, 13, 11, 7, "w"), b(1, 6.5, 8, 15, 9.3, 16, "c")]
    foot = [b(0, 0, 14, 2, 10, 16, "l"), b(14, 0, 14, 16, 10, 16, "l"), b(2, 3, 14.5, 14, 9, 16, "p"),
            b(0, 3, 0, 16, 6, 14.5, "p"), b(1, 6, 0, 15, 9, 14.5, "w"), b(1, 6.5, 0, 15, 9.3, 14, "c"), b(0.8, 3, 0, 1, 9.3, 14, "c")]
    return head, foot


def write_bed(bid, ja, en, tex, futon, recipe, tab):
    head, foot = bed_parts(tex, futon)
    mh = emit_model(f"{bid}_head", head, tex)
    mf = emit_model(f"{bid}_foot", foot, tex)
    v = {}
    for f, y in BLOCKSTATE_Y.items():
        for part, m in (("head", mh), ("foot", mf)):
            for occ in ("false", "true"):
                e = {"model": m}
                if y:
                    e["y"] = y
                v[f"facing={f},occupied={occ},part={part}"] = e
    wj(f"{A}/blockstates/{bid}.json", {"variants": v})
    # アイテム：2マス分を並べたもの
    item = [E(e.f, e.t, e.tex, faces=e.faces) for e in head]
    for e in foot:
        item.append(E((e.f[0], e.f[1], e.f[2] + 16), (e.t[0], e.t[1], e.t[2] + 16), e.tex, faces=e.faces))
    wj(f"{A}/models/item/{bid}.json", model_json(item, tex, display={
        "gui": {"rotation": [30, 160, 0], "translation": [2, 3, 0], "scale": [0.5325, 0.5325, 0.5325]},
        "ground": {"rotation": [0, 0, 0], "translation": [0, 3, 0], "scale": [0.25, 0.25, 0.25]},
        "fixed": {"rotation": [0, 180, 0], "translation": [0, 0, 0], "scale": [0.5, 0.5, 0.5]},
        "thirdperson_righthand": {"rotation": [30, 160, 0], "translation": [0, 3, 1], "scale": [0.375, 0.375, 0.375]},
        "firstperson_righthand": {"rotation": [30, 160, 0], "translation": [0, 3, 0], "scale": [0.375, 0.375, 0.375]}}))
    pool = {"rolls": 1, "entries": [{"type": "minecraft:item", "name": f"{NS}:{bid}"}],
            "conditions": [{"condition": "minecraft:survives_explosion"},
                           {"condition": "minecraft:block_state_property", "block": f"{NS}:{bid}", "properties": {"part": "head"}}]}
    wj(f"{D}/loot_table/blocks/{bid}.json", {"type": "minecraft:block", "pools": [pool]})
    LANG_JA[f"block.{NS}.{bid}"] = ja
    LANG_EN[f"block.{NS}.{bid}"] = en
    RECIPES.append((bid, 1) + recipe)
    BEDS.append({"id": bid, "tab": tab, "futon": futon})


def emit_model(name, els, tex):
    wj(f"{A}/models/block/{name}.json", model_json(els, tex))
    return f"{NS}:block/{name}"


# ---------------- 障子・ふすま（ドア）

DOORS = []


def write_door(did, ja, en, recipe):
    t = {"bottom": f"{NS}:block/{did}_bottom", "top": f"{NS}:block/{did}_top"}
    names = {}
    for half in ("bottom", "top"):
        for hinge in ("left", "right"):
            for op in ("", "_open"):
                n = f"{did}_{half}_{hinge}{op}"
                wj(f"{A}/models/block/{n}.json", {"parent": f"minecraft:block/door_{half}_{hinge}{op}", "textures": t, "render_type": "minecraft:cutout"})
                names[(half, hinge, op)] = f"{NS}:block/{n}"
    v = {}
    rot = {"east": 0, "south": 90, "west": 180, "north": 270}
    for facing, r in rot.items():
        for half, hk in (("lower", "bottom"), ("upper", "top")):
            for hinge in ("left", "right"):
                for opened in ("false", "true"):
                    if opened == "false":
                        m, y = names[(hk, hinge, "")], r
                    else:
                        m = names[(hk, hinge, "_open")]
                        y = (r + (90 if hinge == "left" else 270)) % 360
                    e = {"model": m}
                    if y:
                        e["y"] = y
                    v[f"facing={facing},half={half},hinge={hinge},open={opened}"] = e
    wj(f"{A}/blockstates/{did}.json", {"variants": v})
    wj(f"{A}/models/item/{did}.json", {"parent": "minecraft:item/generated", "textures": {"layer0": f"{NS}:item/{did}"}})
    pool = {"rolls": 1, "entries": [{"type": "minecraft:item", "name": f"{NS}:{did}"}],
            "conditions": [{"condition": "minecraft:survives_explosion"},
                           {"condition": "minecraft:block_state_property", "block": f"{NS}:{did}", "properties": {"half": "lower"}}]}
    wj(f"{D}/loot_table/blocks/{did}.json", {"type": "minecraft:block", "pools": [pool]})
    LANG_JA[f"block.{NS}.{did}"] = ja
    LANG_EN[f"block.{NS}.{did}"] = en
    RECIPES.append((did, 2) + recipe)
    DOORS.append({"id": did})


def main():
    make_textures()
    for fur in SPECS:
        write_furniture(fur)
    for w, wja, wen in WOODS:
        T = wood_tex(w)
        T = {"p": T["p"], "l": T["l"], "w": f"{NS}:block/bed_sheet", "c": f"{NS}:block/bed_sheet"}
        it = wood_items(w)
        T["c"] = "minecraft:block/light_blue_wool"
        write_bed(f"{w}_bed", f"{wja}のベッド", f"{wen} Bed", T, False,
                  (["WWW", "BBB", "PLP"], {"W": "minecraft:white_wool", "B": "minecraft:light_blue_wool", "P": it["P"], "L": it["L"]}), "west")
    write_bed("futon", "布団", "Futon", {"w": f"{NS}:block/bed_sheet", "c": f"{NS}:block/futon_cover"}, True,
              (["BBB", "WWW"], {"B": "minecraft:blue_wool", "W": "minecraft:white_carpet"}), "wa")
    write_door("shoji", "障子", "Shoji Door", (["SPS", "SPS", "SPS"], {"S": "minecraft:stick", "P": "minecraft:paper"}))
    write_door("fusuma", "ふすま", "Fusuma Door", (["PPP", "PGP", "PPP"], {"P": "minecraft:paper", "G": "minecraft:green_dye"}))

    # Java が読む一覧
    out = []
    for fur in SPECS:
        out.append({
            "id": fur.id, "kind": fur.kind, "tab": fur.tab, "tall": fur.tall, "full": fur.full, "seat": fur.seat, "rows": fur.rows,
            "light": fur.light, "sound": fur.sound, "wall": fur.wall, "hanging": fur.hanging, "particles": fur.particles,
            "furin": fur.furin, "passable": fur.passable, "tool": fur.tool,
            "shape": boxes(fur.els), "open": boxes(fur.open_els) if fur.open_els else None,
        })
    wj(f"{RES}/jsn_furniture_specs.json", {"furniture": out, "beds": BEDS, "doors": DOORS})

    # レシピ（同じ並べ方がないか確かめる）
    seen = {}
    for rid, cnt, pat, keys in RECIPES:
        sig = json.dumps(["".join(keys.get(ch, " ") + "," for ch in row) for row in pat])
        assert sig not in seen, f"レシピがかぶっています: {rid} と {seen[sig]}"
        seen[sig] = rid
        key = {}
        for k, v in keys.items():
            key[k] = {"tag": v[1:]} if v.startswith("#") else {"item": v}
        wj(f"{D}/recipe/{rid}.json", {"type": "minecraft:crafting_shaped", "category": "building", "pattern": pat, "key": key,
                                      "result": {"id": f"{NS}:{rid}", "count": cnt}})

    # 道具タグ
    axe = [f"{NS}:{f.id}" for f in SPECS if f.tool == "axe"] + [f"{NS}:{x['id']}" for x in BEDS + DOORS]
    pick = [f"{NS}:{f.id}" for f in SPECS if f.tool == "pickaxe"]
    wj(f"{RES}/data/minecraft/tags/block/mineable/axe.json", {"replace": False, "values": axe})
    wj(f"{RES}/data/minecraft/tags/block/mineable/pickaxe.json", {"replace": False, "values": pick})

    # 名前
    LANG_JA.update({"itemGroup.jsn_furniture.west": "jsn家具（洋風）", "itemGroup.jsn_furniture.wa": "jsn家具（和風）",
                    "entity.jsn_furniture.seat": "座る場所", "container.jsn_furniture.storage": "しまう場所"})
    LANG_EN.update({"itemGroup.jsn_furniture.west": "jsn Furniture (Western)", "itemGroup.jsn_furniture.wa": "jsn Furniture (Japanese)",
                    "entity.jsn_furniture.seat": "Seat", "container.jsn_furniture.storage": "Storage"})
    for key, ja, en in (("furin_glass", "風鈴（ガラス）が鳴る", "Glass wind chime rings"), ("furin_iron", "風鈴（鉄）が鳴る", "Iron wind chime rings"),
                        ("furin_bamboo", "風鈴（竹）が鳴る", "Bamboo wind chime clacks"), ("furin_ceramic", "風鈴（陶器）が鳴る", "Ceramic wind chime rings"),
                        ("furin_brass", "風鈴（真鍮）が鳴る", "Brass wind chime rings"), ("shishi_odoshi", "鹿威しが鳴る", "Shishi-odoshi knocks")):
        LANG_JA[f"subtitles.jsn_furniture.{key}"] = ja
        LANG_EN[f"subtitles.jsn_furniture.{key}"] = en
    wj(f"{A}/lang/ja_jp.json", LANG_JA)
    wj(f"{A}/lang/en_us.json", LANG_EN)
    print(f"家具 {len(SPECS)}・ベッド {len(BEDS)}・ドア {len(DOORS)}・レシピ {len(RECIPES)}")


main()
