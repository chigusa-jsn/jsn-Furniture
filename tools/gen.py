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
                 furin="", tool="axe", passable=False, hanging=False, recipe=None, count=1, anim="", instrument="", parts=None, static=None):
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
    {"p": "minecraft:block/oak_planks", "m": IRON, "q": "jsn_furniture:block/water"}, sound="metal", tool="pickaxe",
    recipe=(["I I", "IWI", "PPP"], {"I": "minecraft:iron_ingot", "W": "minecraft:water_bucket", "P": "#minecraft:planks"})))
add(F("bathtub", "お風呂", "Bathtub", "seat", [
    b(0, 0, 0, 16, 2, 16, "q"), b(0, 2, 0, 16, 10, 1.5, "q"), b(0, 2, 14.5, 16, 10, 16, "q"), b(0, 2, 1.5, 1.5, 10, 14.5, "q"),
    b(14.5, 2, 1.5, 16, 10, 14.5, "q"), b(1.5, 7, 1.5, 14.5, 7.5, 14.5, "a", shape=False)],
    {"q": QUARTZ, "a": "jsn_furniture:block/water"}, seat=3, sound="stone", tool="pickaxe",
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
      {"c": "jsn_furniture:block/clock_face", "d": "minecraft:block/dark_oak_planks", "h": "minecraft:block/black_concrete"}, wall=True, sound="wood",
      parts={"hour": [b(7.6, 8, 14.7, 8.4, 10.8, 14.9, "h")], "min": [b(7.7, 8, 14.5, 8.3, 12, 14.7, "h")]}, anim="clock",
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
    {"t": "minecraft:block/brown_terracotta", "l": "minecraft:block/spruce_log", "f": "minecraft:block/azalea_leaves"},
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

# ------------------------------------------------------------ 動物（風鈴・縁起物・ぬいぐるみ・ペット・動物の形の家具）
ANIMAL = {
    # 名前: (毛の色, 顔の描き方, 耳)
    "cat_white": ((238, 238, 236), "cat", "cat"), "cat_black": ((40, 40, 46), "cat_black", "cat"),
    "cat_calico": ((240, 236, 228), "cat", "cat"), "cat_gray": ((140, 140, 148), "cat", "cat"),
    "fox": ((222, 120, 45), "fox", "fox"), "rabbit": ((245, 242, 240), "rabbit", "rabbit"),
    "tanuki": ((120, 95, 70), "tanuki", "round"), "shiba": ((214, 150, 80), "shiba", "cat"),
    "bear": ((130, 85, 50), "bear", "round"), "panda": ((245, 245, 245), "panda", "round_black"),
    "penguin": ((40, 45, 60), "penguin", None), "chick": ((250, 215, 70), "chick", None),
}
ANIMAL_JA = {"cat_white": "白猫", "cat_black": "黒猫", "cat_calico": "三毛猫", "cat_gray": "灰色の猫", "fox": "狐", "rabbit": "うさぎ",
             "tanuki": "たぬき", "shiba": "柴犬", "bear": "くま", "panda": "パンダ", "penguin": "ペンギン", "chick": "ひよこ"}
ANIMAL_EN = {"cat_white": "White Cat", "cat_black": "Black Cat", "cat_calico": "Calico Cat", "cat_gray": "Gray Cat", "fox": "Fox", "rabbit": "Rabbit",
             "tanuki": "Tanuki", "shiba": "Shiba Dog", "bear": "Bear", "panda": "Panda", "penguin": "Penguin", "chick": "Chick"}


def ears(kind, x1, x2, y, z1, tex="u", dark="k", shape=False):
    """頭の上の耳。x1..x2 が頭の幅、y が頭のてっぺん"""
    w = x2 - x1
    if kind == "cat":
        return [b(x1 + 0.3, y, z1 + 1, x1 + 2.3, y + 2, z1 + 2.5, tex, shape=shape), b(x2 - 2.3, y, z1 + 1, x2 - 0.3, y + 2, z1 + 2.5, tex, shape=shape)]
    if kind == "fox":
        return [b(x1, y, z1 + 1, x1 + 2.5, y + 3, z1 + 2.5, tex, shape=shape), b(x2 - 2.5, y, z1 + 1, x2, y + 3, z1 + 2.5, tex, shape=shape)]
    if kind == "rabbit":
        return [b(x1 + 1, y, z1 + 1.5, x1 + 2.5, y + 5, z1 + 2.5, tex, shape=shape), b(x2 - 2.5, y, z1 + 1.5, x2 - 1, y + 5, z1 + 2.5, tex, shape=shape)]
    if kind in ("round", "round_black"):
        t = dark if kind == "round_black" else tex
        return [b(x1, y - 0.5, z1 + 1.5, x1 + 2, y + 1.5, z1 + 3, t, shape=shape), b(x2 - 2, y - 0.5, z1 + 1.5, x2, y + 1.5, z1 + 3, t, shape=shape)]
    return []


def head(x1, y1, z1, x2, y2, z2, kind, shape=True):
    """前（北）に顔、ほかは毛"""
    return [b(x1, y1, z1, x2, y2, z2, {"north": "q", "south": "u", "east": "u", "west": "u", "up": "u", "down": "u"},
              uv={"north": [0, 0, 16, 16]}, shape=shape)] + ears(ANIMAL[kind][2], x1, x2, y2, z1)


def animal_tex(kind):
    return {"u": f"jsn_furniture:block/fur_{kind}", "q": f"jsn_furniture:block/face_{kind}", "k": "jsn_furniture:block/fur_black",
            "w": "jsn_furniture:block/fur_white"}


# 動物の風鈴
for a in ("cat_white", "cat_black", "cat_calico", "fox", "rabbit", "tanuki"):
    fid = f"furin_{a}"
    body = [b(7.7, 12, 7.7, 8.3, 14, 8.3, "h")] + head(5, 6, 5, 11, 11.5, 11, a, shape=False) + [
        b(7.8, 2, 7.95, 8.2, 6, 8.05, "h"), b(6.8, -5, 7.95, 9.2, 2, 8.05, "t")]
    tex = animal_tex(a) | {"h": "minecraft:block/white_wool", "t": "jsn_furniture:block/tanzaku"}
    FURIN.append((fid, f"{ANIMAL_JA[a]}の風鈴", f"{ANIMAL_EN[a]} Wind Chime", "glass", "minecraft:glass_pane",
                  {"cat_white": "minecraft:white_wool", "cat_black": "minecraft:black_wool", "cat_calico": "minecraft:orange_wool",
                   "fox": "minecraft:sweet_berries", "rabbit": "minecraft:rabbit_hide", "tanuki": "minecraft:brown_wool"}[a], ("animal", a)))
    add(F(fid, f"{ANIMAL_JA[a]}の風鈴", f"{ANIMAL_EN[a]} Wind Chime", "furin", furin_hook(), tex, body=body, furin="glass",
          tab="wa", hanging=True, sound="glass", tool="pickaxe",
          recipe=(["S", "G", "X"], {"S": "minecraft:string", "G": "minecraft:glass_pane", "X": FURIN[-1][5]})))

# 縁起物
MANEKI = [b(4, 0, 5, 12, 8, 12, "u"), b(4, 7.5, 4.8, 12, 8.5, 11.7, "r", shape=False), b(7.3, 6.3, 4.2, 8.7, 7.7, 5, "g", shape=False),
          b(11.5, 8.5, 6, 14, 14, 8.5, "u", shape=False), b(5, 0, 4, 7, 2, 5, "u", shape=False)]
for mid, mja, men, fur in (("maneki_neko", "招き猫", "Maneki-neko", "cat_white"), ("maneki_neko_gold", "金の招き猫", "Golden Maneki-neko", "gold")):
    t = animal_tex("cat_white") | {"r": "minecraft:block/red_wool", "g": "minecraft:block/gold_block"}
    if fur == "gold":
        t["u"] = "minecraft:block/gold_block"
        t["q"] = "jsn_furniture:block/face_maneki_gold"
    else:
        t["q"] = "jsn_furniture:block/face_maneki"
    add(F(mid, mja, men, "basic", MANEKI + head(3.5, 8, 4.5, 12.5, 14.5, 11.5, "cat_white"), t, tab="wa", sound="stone", tool="pickaxe",
          recipe=(["C", "D", "X"], {"C": "minecraft:clay_ball", "D": "minecraft:white_dye", "X": "minecraft:gold_nugget" if fur != "gold" else "minecraft:gold_ingot"}) if fur != "gold" else
          (["GGG", "GCG", "GGG"], {"G": "minecraft:gold_ingot", "C": f"{NS}:maneki_neko"})))
add(F("kitsune_statue", "お稲荷さんの狐", "Inari Fox Statue", "basic", [
    b(2, 0, 2, 14, 4, 14, "s"), b(5, 4, 5, 11, 12, 12, "s"), b(5, 9, 4.6, 11, 12, 5.2, "r", shape=False),
    b(4.5, 12, 3, 11.5, 17, 10, {"north": "q", "south": "s", "east": "s", "west": "s", "up": "s", "down": "s"}, uv={"north": [0, 0, 16, 16]}, shape=False),
    b(4.5, 17, 5, 6.5, 20, 6.5, "s", shape=False), b(9.5, 17, 5, 11.5, 20, 6.5, "s", shape=False), b(7, 4, 12, 9, 13, 15, "s", shape=False)],
    {"s": "minecraft:block/stone", "r": "minecraft:block/red_wool", "q": "jsn_furniture:block/face_kitsune_statue"}, tab="wa", sound="stone", tool="pickaxe",
    recipe=(["SRS", "SSS", "SSS"], {"S": "minecraft:stone", "R": "minecraft:red_wool"})))
add(F("tanuki_okimono", "信楽のたぬき", "Shigaraki Tanuki", "basic", [
    b(3, 0, 4, 13, 10, 13, "u"), b(5, 3, 3.5, 11, 9, 4, "w", shape=False),
    b(4, 10, 3.5, 12, 16, 11.5, {"north": "q", "south": "u", "east": "u", "west": "u", "up": "u", "down": "u"}, uv={"north": [0, 0, 16, 16]}),
    b(2.5, 16, 2, 13.5, 17, 13, "h", shape=False), b(5, 17, 4.5, 11, 19, 10.5, "h", shape=False),
    b(12, 0, 3, 14.5, 5, 5.5, "w", shape=False), b(12.5, 5, 3.5, 14, 6, 5, "w", shape=False)] + ears("round", 4, 12, 16, 3.5),
    animal_tex("tanuki") | {"h": "minecraft:block/hay_block_top", "w": "minecraft:block/white_terracotta"}, tab="wa", sound="stone", tool="pickaxe",
    recipe=(["H", "C", "C"], {"H": "minecraft:wheat", "C": "minecraft:brown_terracotta"})))
for col, cja, cen in (("red", "赤", "Red"), ("white", "白", "White")):
    add(F(f"daruma_{col}", f"{cja}いだるま", f"{cen} Daruma", "basic", [
        b(3, 0, 3, 13, 11, 13, {"north": "q", "south": "u", "east": "u", "west": "u", "up": "u", "down": "u"}, uv={"north": [0, 0, 16, 16]}),
        b(4, 11, 4, 12, 12.5, 12, "u", shape=False)],
        {"u": f"minecraft:block/{col}_concrete", "q": f"jsn_furniture:block/face_daruma_{col}"}, tab="wa", sound="wood",
        recipe=([" D ", "PWP", " P "], {"D": f"minecraft:{col}_dye", "P": "minecraft:paper", "W": "minecraft:black_dye"})))

# ぬいぐるみ
PLUSHES = ("cat_white", "fox", "shiba", "rabbit", "bear", "panda", "penguin", "chick")
for a in PLUSHES:
    t = animal_tex(a)
    if a in ("penguin", "chick"):
        els = [b(4.5, 0, 5, 11.5, 9, 11, {"north": "q", "south": "u", "east": "u", "west": "u", "up": "u", "down": "u"}, uv={"north": [0, 0, 16, 16]}),
               b(3.5, 2, 6.5, 4.5, 7, 9.5, "u", shape=False), b(11.5, 2, 6.5, 12.5, 7, 9.5, "u", shape=False),
               b(5.5, 0, 4, 7.5, 1, 6, "o", shape=False), b(8.5, 0, 4, 10.5, 1, 6, "o", shape=False)]
        t["o"] = "minecraft:block/orange_concrete"
    else:
        limb = "k" if a == "panda" else "u"
        els = [b(5, 0, 6, 11, 6, 11, "u"), b(5, 0, 4, 7, 2, 6, limb, shape=False), b(9, 0, 4, 11, 2, 6, limb, shape=False),
               b(4, 2, 7, 5, 5, 9, limb, shape=False), b(11, 2, 7, 12, 5, 9, limb, shape=False)] + head(4, 6, 4.5, 12, 12, 10.5, a)
        tail = {"fox": [b(7, 0, 11, 9, 4, 15, "u", shape=False), b(7, 0, 14, 9, 2, 16, "w", shape=False)], "rabbit": [b(7, 1, 11, 9, 3, 12.5, "u", shape=False)],
                "shiba": [b(7, 4, 10.5, 9, 7, 12.5, "u", shape=False)], "cat_white": [b(7.5, 0, 11, 8.5, 6, 12, "u", shape=False)]}.get(a, [])
        els += tail
    add(F(f"plush_{a}", f"{ANIMAL_JA[a]}のぬいぐるみ", f"{ANIMAL_EN[a]} Plush", "basic", els, t, tab="west", sound="wool",
          recipe=([" W ", "WXW", " W "], {"W": "minecraft:white_wool" if a in ("cat_white", "rabbit", "panda") else
                                         {"fox": "minecraft:orange_wool", "shiba": "minecraft:orange_wool", "bear": "minecraft:brown_wool",
                                          "penguin": "minecraft:black_wool", "chick": "minecraft:yellow_wool"}[a],
                                          "X": {"cat_white": "minecraft:string", "fox": "minecraft:sweet_berries", "shiba": "minecraft:bone",
                                                "rabbit": "minecraft:carrot", "bear": "minecraft:honeycomb", "panda": "minecraft:bamboo",
                                                "penguin": "minecraft:cod", "chick": "minecraft:egg"}[a]})))

# ペット用
add(F("cat_tower", "キャットタワー", "Cat Tower", "pet", [
    b(0, 0, 0, 16, 2, 16, "c"), b(6, 2, 6, 10, 28, 10, "r"), b(1, 13, 1, 15, 15, 15, "c"), b(1, 27, 1, 15, 29, 15, "c"),
    b(1, 29, 1, 15, 31, 2, "c", shape=False), b(1, 29, 14, 15, 31, 15, "c", shape=False), b(1, 29, 2, 2, 31, 14, "c", shape=False), b(14, 29, 2, 15, 31, 14, "c", shape=False),
    b(11, 7, 2, 13, 13, 4, "f", shape=False)],
    {"c": "minecraft:block/light_gray_wool", "r": "jsn_furniture:block/sisal", "f": "jsn_furniture:block/fur_cat_white"},
    tall=True, seat=29, sound="wool", recipe=(["WWW", " S ", "WSW"], {"W": "minecraft:light_gray_wool", "S": "minecraft:string"})))
add(F("dog_house", "犬小屋", "Dog House", "pet", [
    b(1, 0, 2, 15, 1, 15, "p"), b(1, 1, 14, 15, 12, 15, "p"), b(1, 1, 2, 2, 12, 14, "p"), b(14, 1, 2, 15, 12, 14, "p"),
    b(1, 1, 1, 5, 12, 2, "p"), b(11, 1, 1, 15, 12, 2, "p"), b(5, 9, 1, 11, 12, 2, "p"),
    b(-0.5, 11, 0.5, 8.5, 12, 15.5, "r", shape=False, rot={"origin": [8, 12, 8], "axis": "z", "angle": 22.5}),
    b(7.5, 11, 0.5, 16.5, 12, 15.5, "r", shape=False, rot={"origin": [8, 12, 8], "axis": "z", "angle": -22.5}),
    b(6, 13, 1.5, 10, 15, 2, "n", shape=False)],
    {"p": "minecraft:block/oak_planks", "r": "minecraft:block/red_concrete", "n": "jsn_furniture:block/dog_house_sign"}, seat=1, sound="wood",
    recipe=(["RRR", "P P", "PPP"], {"R": "minecraft:red_dye", "P": "#minecraft:planks"})))
for c, cja, cen in COLORS:
    add(F(f"{c}_pet_bed", f"{cja}のペットベッド", f"{cen} Pet Bed", "pet", [
        b(1, 0, 1, 15, 1.5, 15, "w"), b(1, 1.5, 1, 15, 4, 3, "w"), b(1, 1.5, 13, 15, 4, 15, "w"), b(1, 1.5, 3, 3, 4, 13, "w"), b(13, 1.5, 3, 15, 4, 13, "w"),
        b(3, 1.5, 3, 13, 2, 13, "i", shape=False)],
        {"w": f"minecraft:block/{c}_wool", "i": "minecraft:block/white_wool" if c != "white" else "minecraft:block/light_gray_wool"},
        seat=2, sound="wool", recipe=(["W W", "WWW"], {"W": f"minecraft:{c}_wool"})))
BOWL = [b(4, 0, 4, 12, 1, 12, "b"), b(4, 1, 4, 12, 3, 5, "b"), b(4, 1, 11, 12, 3, 12, "b"), b(4, 1, 5, 5, 3, 11, "b"), b(11, 1, 5, 12, 3, 11, "b"),
        b(5, 1, 5, 11, 2.3, 11, "f", shape=False)]
add(F("food_bowl", "えさ皿", "Food Bowl", "basic", BOWL,
      {"b": "minecraft:block/red_terracotta", "f": "jsn_furniture:block/pet_food"}, sound="stone", tool="pickaxe",
      recipe=(["B", "T"], {"B": "minecraft:bone_meal", "T": "minecraft:red_terracotta"})))
add(F("water_bowl", "水皿", "Water Bowl", "basic", BOWL,
      {"b": "minecraft:block/blue_terracotta", "f": "jsn_furniture:block/water"}, sound="stone", tool="pickaxe",
      recipe=(["W", "T"], {"W": "minecraft:water_bucket", "T": "minecraft:blue_terracotta"})))

# 動物の形の家具
for a in ("cat_white", "cat_black", "cat_calico", "cat_gray"):
    add(F(f"neko_cushion_{a.split('_')[1]}", f"{ANIMAL_JA[a]}のクッション", f"{ANIMAL_EN[a]} Cushion", "seat", [
        b(2, 0, 3, 14, 3, 14, "u"), b(2, 0, 2, 14, 5, 3, {"north": "q", "south": "u", "east": "u", "west": "u", "up": "u", "down": "u"}, uv={"north": [0, 0, 16, 16]}, shape=False)]
        + ears("cat", 2, 14, 5, 1.5), animal_tex(a), seat=3, sound="wool",
        recipe=(["S S", "WWW"], {"S": "minecraft:string", "W": {"cat_white": "minecraft:white_wool", "cat_black": "minecraft:black_wool",
                                                              "cat_calico": "minecraft:orange_wool", "cat_gray": "minecraft:gray_wool"}[a]})))
for c, cja, cen in COLORS:
    add(F(f"{c}_paw_rug", f"{cja}の肉球ラグ", f"{cen} Paw Rug", "basic", [b(0, 0, 0, 16, 1, 16, {"up": "p", "down": "w", "north": "w", "south": "w", "east": "w", "west": "w"}, uv={"up": [0, 0, 16, 16]})],
          {"w": f"minecraft:block/{c}_wool", "p": f"jsn_furniture:block/paw_rug_{c}"}, sound="wool",
          recipe=(["CBC"], {"C": f"minecraft:{c}_carpet", "B": "minecraft:bone"}), count=2))
for a, sja, sen, wool in (("bear", "くまのソファ", "Bear Sofa", "brown"), ("cat_white", "ねこのソファ", "Cat Sofa", "white")):
    t = animal_tex(a)
    add(F(f"{'kuma' if a == 'bear' else 'neko'}_sofa", sja, sen, "seat", [
        b(0, 0, 1, 16, 7, 15, "u"), b(0, 7, 11, 16, 15, 15, {"north": "q", "south": "u", "east": "u", "west": "u", "up": "u", "down": "u"}, uv={"north": [0, 0, 16, 16]}, shape=False),
        b(0, 7, 1, 2, 11, 11, "u"), b(14, 7, 1, 16, 11, 11, "u")] + ears("round" if a == "bear" else "cat", 0, 16, 15, 10.5), t, seat=8, sound="wool",
        recipe=(["X  ", "WWW", "PPP"], {"X": "minecraft:honeycomb" if a == "bear" else "minecraft:string", "W": f"minecraft:{wool}_wool", "P": "#minecraft:planks"})))


# ------------------------------------------------------------ 動物をもっと（マイクラのモブ・シマエナガ・カピバラ）
MORE = {
    # id: (毛の色, 顔, 耳, 体の形, 日本語, 英語, 羊毛, 特別な材料)
    "wolf": ((200, 200, 205), "wolf", "fox", "quad", "オオカミ", "Wolf", "light_gray", "minecraft:bone"),
    "polar_bear": ((242, 242, 238), "polar_bear", "round", "quad", "シロクマ", "Polar Bear", "white", "minecraft:salmon"),
    "axolotl": ((240, 160, 190), "axolotl", "gills", "axolotl", "ウーパールーパー", "Axolotl", "pink", "minecraft:tropical_fish_bucket"),
    "frog": ((120, 165, 75), "frog", "frog", "frog", "カエル", "Frog", "lime", "minecraft:slime_ball"),
    "bee": ((245, 200, 60), "bee", "antenna", "bee", "ハチ", "Bee", "yellow", "minecraft:honeycomb"),
    "sheep": ((245, 245, 245), "sheep", "side", "quad", "ヒツジ", "Sheep", "white", "minecraft:mutton"),
    "pig": ((240, 165, 165), "pig", "side", "quad", "ブタ", "Pig", "pink", "minecraft:carrot"),
    "cow": ((245, 245, 245), "cow", "horn", "quad", "ウシ", "Cow", "black", "minecraft:leather"),
    "chicken": ((245, 245, 245), "chicken", "comb", "bird", "ニワトリ", "Chicken", "white", "minecraft:feather"),
    "parrot": ((220, 40, 40), "parrot", None, "bird", "オウム", "Parrot", "red", "minecraft:wheat_seeds"),
    "turtle": ((100, 160, 85), "turtle", None, "turtle", "カメ", "Turtle", "green", "minecraft:seagrass"),
    "allay": ((110, 200, 240), "allay", None, "allay", "アレイ", "Allay", "light_blue", "minecraft:amethyst_shard"),
    "enaga": ((250, 250, 250), "enaga", None, "ball", "シマエナガ", "Long-tailed Tit", "white", "minecraft:snowball"),
    "capybara": ((160, 112, 72), "capybara", "round", "capy", "カピバラ", "Capybara", "brown", "minecraft:sugar_cane"),
}
for k, v in MORE.items():
    ANIMAL[k] = (v[0], v[1], v[2])
    ANIMAL_JA[k] = v[4]
    ANIMAL_EN[k] = v[5]


def ears2(kind, x1, x2, y, z1, tex="u"):
    """追加の動物の耳など"""
    if kind == "gills":
        out = []
        for i, yy in enumerate((y - 1, y - 2.5, y - 4)):
            out.append(b(x1 - 1.5 + i * 0.3, yy, z1 + 1, x1, yy + 1, z1 + 2, "e", shape=False))
            out.append(b(x2, yy, z1 + 1, x2 + 1.5 - i * 0.3, yy + 1, z1 + 2, "e", shape=False))
        return out
    if kind == "frog":
        return [b(x1 + 0.5, y, z1, x1 + 3, y + 2, z1 + 2.5, "u", shape=False), b(x2 - 3, y, z1, x2 - 0.5, y + 2, z1 + 2.5, "u", shape=False),
                b(x1 + 1, y + 0.5, z1 - 0.1, x1 + 2.5, y + 1.8, z1, "k", shape=False), b(x2 - 2.5, y + 0.5, z1 - 0.1, x2 - 1, y + 1.8, z1, "k", shape=False)]
    if kind == "antenna":
        return [b(x1 + 2, y, z1 + 0.5, x1 + 2.5, y + 2.5, z1 + 1, "k", shape=False), b(x2 - 2.5, y, z1 + 0.5, x2 - 2, y + 2.5, z1 + 1, "k", shape=False)]
    if kind == "side":
        return [b(x1 - 2, y - 2, z1 + 1, x1, y - 1, z1 + 2.5, "e", shape=False), b(x2, y - 2, z1 + 1, x2 + 2, y - 1, z1 + 2.5, "e", shape=False)]
    if kind == "horn":
        return [b(x1 - 1, y - 1, z1 + 1.5, x1 + 0.5, y + 1.5, z1 + 2.5, "h", shape=False), b(x2 - 0.5, y - 1, z1 + 1.5, x2 + 1, y + 1.5, z1 + 2.5, "h", shape=False),
                b(x1 - 2, y - 2.5, z1 + 1.5, x1, y - 1.5, z1 + 3, "u", shape=False), b(x2, y - 2.5, z1 + 1.5, x2 + 2, y - 1.5, z1 + 3, "u", shape=False)]
    if kind == "comb":
        return [b(x1 + 3, y, z1 + 0.5, x2 - 3, y + 2, z1 + 3, "r", shape=False)]
    return ears(kind, x1, x2, y, z1, tex)


def head2(x1, y1, z1, x2, y2, z2, a, shape=True):
    return [b(x1, y1, z1, x2, y2, z2, {"north": "q", "south": "u", "east": "u", "west": "u", "up": "u", "down": "u"},
              uv={"north": [0, 0, 16, 16]}, shape=shape)] + ears2(ANIMAL[a][2], x1, x2, y2, z1)


def tex2(a):
    t = animal_tex(a)
    t.update({"e": {"axolotl": "jsn_furniture:block/fur_axolotl_gill", "sheep": "jsn_furniture:block/face_sheep",
                    "pig": "jsn_furniture:block/fur_pig", "cow": "jsn_furniture:block/fur_black"}.get(a, t["u"]),
              "h": "minecraft:block/white_terracotta", "r": "minecraft:block/red_wool", "o": "minecraft:block/orange_concrete",
              "y": "minecraft:block/yellow_concrete", "g": "jsn_furniture:block/wing", "s": "jsn_furniture:block/fur_turtle_shell"})
    return t


def plush2(a):
    body = MORE[a][3]
    if body == "quad":
        tail = {"wolf": [b(7, 2, 11, 9, 4, 15, "u", shape=False)], "pig": [b(7.5, 3, 11, 8.5, 4, 12, "u", shape=False)],
                "cow": [b(7.5, 1, 11, 8.5, 5, 11.5, "u", shape=False)], "sheep": [b(7, 3, 11, 9, 5, 12, "u", shape=False)],
                "polar_bear": [b(7, 2, 11, 9, 4, 12, "u", shape=False)]}.get(a, [])
        big = 0.5 if a in ("polar_bear", "sheep") else 0
        return [b(5 - big, 0, 6, 11 + big, 6 + big, 11 + big, "u"), b(5, 0, 4, 7, 2, 6, "u", shape=False), b(9, 0, 4, 11, 2, 6, "u", shape=False)] + \
            head2(4, 6, 4.5, 12, 12, 10.5, a) + tail
    if body == "capy":
        return [b(3.5, 0, 5, 12.5, 7, 13, "u"), b(4, 0, 4, 6, 1.5, 6, "u", shape=False), b(10, 0, 4, 12, 1.5, 6, "u", shape=False)] + \
            head2(4.5, 4, 1.5, 11.5, 11, 7, a) + [b(6, 11, 3.5, 10, 12, 6.5, "y", shape=False)]  # 頭に柚子をのせて
    if body == "ball":  # シマエナガ：まんまるの白いもふもふと、長いしっぽ
        return [b(4, 0, 4, 12, 8, 12, {"north": "q", "south": "u", "east": "u", "west": "u", "up": "u", "down": "u"}, uv={"north": [0, 0, 16, 16]}),
                b(3.6, 3, 7.5, 4, 5, 10.5, "k", shape=False), b(12, 3, 7.5, 12.4, 5, 10.5, "k", shape=False),
                b(7.2, 1.5, 12, 8.8, 2.3, 16, "k", shape=False), b(6, 0, 5, 7, 0.5, 6, "k", shape=False), b(9, 0, 5, 10, 0.5, 6, "k", shape=False)]
    if body == "bird":
        tail = [b(6.5, 1, 11, 9.5, 5, 13, "u" if a == "chicken" else "y", shape=False)]
        extra = [b(7, 4, 4, 9, 6, 4.5, "r", shape=False)] if a == "chicken" else [b(3.5, 3, 6, 4.5, 8, 10, "g2", shape=False), b(11.5, 3, 6, 12.5, 8, 10, "g2", shape=False)]
        return [b(4.5, 0, 5, 11.5, 10, 11, {"north": "q", "south": "u", "east": "u", "west": "u", "up": "u", "down": "u"}, uv={"north": [0, 0, 16, 16]})] + \
            ears2(ANIMAL[a][2], 4.5, 11.5, 10, 5) + tail + extra
    if body == "bee":
        return [b(4, 2, 4, 12, 9, 13, {"north": "q", "south": "u", "east": "u", "west": "u", "up": "u", "down": "u"}, uv={"north": [0, 0, 16, 16]}),
                b(5, 9, 7, 8, 9.5, 12, "g", shape=False), b(8, 9, 7, 11, 9.5, 12, "g", shape=False), b(7.5, 4, 13, 8.5, 5, 14.5, "k", shape=False),
                b(5, 0, 6, 6, 2, 7, "k", shape=False), b(10, 0, 6, 11, 2, 7, "k", shape=False)] + ears2("antenna", 4, 12, 9, 4)
    if body == "turtle":
        return [b(3, 0, 4, 13, 3, 13, "u"), b(3.5, 3, 4.5, 12.5, 6, 12.5, "s"), b(6, 1, 1.5, 10, 5, 4.5,
                {"north": "q", "south": "u", "east": "u", "west": "u", "up": "u", "down": "u"}, uv={"north": [0, 0, 16, 16]}, shape=False),
                b(2, 0, 4, 3, 1.5, 6, "u", shape=False), b(13, 0, 4, 14, 1.5, 6, "u", shape=False), b(2, 0, 11, 3, 1.5, 13, "u", shape=False), b(13, 0, 11, 14, 1.5, 13, "u", shape=False)]
    if body == "frog":
        return [b(4, 0, 6, 12, 5, 12, "u"), b(3, 0, 4, 5, 1, 7, "u", shape=False), b(11, 0, 4, 13, 1, 7, "u", shape=False)] + head2(4, 2, 3, 12, 7, 8, a)
    if body == "axolotl":
        return [b(5, 0, 6, 11, 4, 14, "u"), b(7, 0.5, 14, 9, 3, 16, "e", shape=False), b(4, 0, 6, 5, 1, 8, "u", shape=False), b(11, 0, 6, 12, 1, 8, "u", shape=False)] + \
            head2(4.5, 0, 1.5, 11.5, 5.5, 6, a)
    if body == "allay":
        return [b(5.5, 1, 6, 10.5, 6, 10, "u"), b(10.5, 2, 6.5, 13, 6, 7, "g", shape=False), b(3, 2, 6.5, 5.5, 6, 7, "g", shape=False)] + \
            head2(5, 6, 5.5, 11, 11, 10.5, a)
    raise ValueError(a)


for a, (rgb, face, ear, body, ja, en, wool, extra) in MORE.items():
    t = tex2(a)
    t["g2"] = "minecraft:block/green_wool"
    add(F(f"plush_{a}", f"{ja}のぬいぐるみ", f"{en} Plush", "basic", plush2(a), t, tab="west", sound="wool",
          recipe=([" W ", "WXW", " W "], {"W": f"minecraft:{wool}_wool", "X": extra})))
    # 風鈴（顔の形）
    fid = f"furin_{a}"
    body_els = [b(7.7, 12, 7.7, 8.3, 14, 8.3, "fh")] + head2(5, 6, 5, 11, 11.5, 11, a, shape=False) + [
        b(7.8, 2, 7.95, 8.2, 6, 8.05, "fh"), b(6.8, -5, 7.95, 9.2, 2, 8.05, "ft")]
    tf = dict(t)
    tf.update({"fh": "minecraft:block/white_wool", "ft": "jsn_furniture:block/tanzaku"})
    tf["h"] = "minecraft:block/white_wool" if False else tf["h"]
    add(F(fid, f"{ja}の風鈴", f"{en} Wind Chime", "furin", [b(7.6, 14, 7.6, 8.4, 16, 8.4, "fh")], tf, body=body_els, furin="glass",
          tab="wa", hanging=True, sound="glass", tool="pickaxe",
          recipe=(["S", "G", "X"], {"S": "minecraft:string", "G": "minecraft:glass_pane", "X": f"{NS}:plush_{a}"})))
    FURIN.append((fid, "", "", "glass", "", "", ("animal", a)))

# クッション：動物みんな
CUSHION_WOOL = {"fox": "orange", "rabbit": "white", "tanuki": "brown", "shiba": "orange", "bear": "brown", "panda": "white", "penguin": "black", "chick": "yellow"}
CUSHION_WOOL.update({k: v[6] for k, v in MORE.items()})
for a, wool in CUSHION_WOOL.items():
    t = tex2(a)
    els = [b(2, 0, 3, 14, 3, 14, "u"),
           b(2, 0, 2, 14, 5, 3, {"north": "q", "south": "u", "east": "u", "west": "u", "up": "u", "down": "u"}, uv={"north": [0, 0, 16, 16]}, shape=False)]
    els += ears2(ANIMAL[a][2], 2, 14, 5, 1.5) if ANIMAL[a][2] else []
    if a == "turtle":
        els.append(b(3, 3, 4, 13, 4, 13, "s", shape=False))
    if a == "enaga":
        els.append(b(7.2, 0.5, 14, 8.8, 1.3, 17, "k", shape=False))
    add(F(f"cushion_{a}", f"{ANIMAL_JA[a]}のクッション", f"{ANIMAL_EN[a]} Cushion", "seat", els, t, seat=3, sound="wool",
          recipe=(["X", "W"], {"X": f"{NS}:tanuki_okimono" if a == "tanuki" else f"{NS}:plush_{a}", "W": f"minecraft:{wool}_wool"}), count=2))


# ------------------------------------------------------------ お庭・動く家具・遊び・お店
WHITE_C = "minecraft:block/white_concrete"
RED_C = "minecraft:block/red_concrete"
YEL_C = "minecraft:block/yellow_concrete"
BLUE_C = "minecraft:block/blue_concrete"

# ブランコ：わくは動かず、板とつなが前後にゆれる（座ったとき）
add(F("swing", "ブランコ", "Swing", "swing",
      [b(0, 0, 6, 1, 31, 10, "f"), b(15, 0, 6, 16, 31, 10, "f"), b(0, 30, 7, 16, 32, 9, "f"), b(3, 5, 5, 13, 6, 11, "s")],
      {"f": RED_C, "s": "minecraft:block/oak_planks", "c": "minecraft:block/iron_block"},
      static=[b(0, 0, 6, 1, 31, 10, "f"), b(-1, 0, 4, 2, 1, 12, "f"), b(15, 0, 6, 16, 31, 10, "f"), b(14, 0, 4, 17, 1, 12, "f"), b(0, 30, 7, 16, 32, 9, "f")],
      parts={"anim": [b(3, 5, 5, 13, 6.2, 11, "s"), b(3.5, 6, 7.6, 4.2, 30, 8.4, "c"), b(11.8, 6, 7.6, 12.5, 30, 8.4, "c")]},
      anim="swing", seat=6, tool="pickaxe", sound="metal",
      recipe=(["III", "I I", "IPI"], {"I": "minecraft:iron_ingot", "P": "#minecraft:wooden_slabs"})))
# すべり台：てっぺんから前へすべる（前のマスまでスロープがのびる）
SLIDE_ROT = {"origin": [8, 11, -1], "axis": "x", "angle": -45}
add(F("slide", "すべり台", "Slide", "slide",
      [b(1, 0, 14, 2, 22, 16, "y"), b(14, 0, 14, 15, 22, 16, "y"), b(2, 4, 15, 14, 5, 16, "y"), b(2, 9, 15, 14, 10, 16, "y"), b(2, 14, 15, 14, 15, 16, "y"),
       b(1, 0, 6, 2, 20, 8, "y"), b(14, 0, 6, 15, 20, 8, "y"), b(1, 19, 6, 15, 20, 16, "p"), b(1, 20, 7, 2, 24, 15, "y"), b(14, 20, 7, 15, 24, 15, "y"),
       b(2, 10.5, -13.75, 14, 11.5, 11.75, "r", shape=False, rot=SLIDE_ROT), b(1, 11.5, -13.75, 2, 13, 11.75, "y", shape=False, rot=SLIDE_ROT),
       b(14, 11.5, -13.75, 15, 13, 11.75, "y", shape=False, rot=SLIDE_ROT)],
      {"y": YEL_C, "r": RED_C, "p": BLUE_C}, tool="pickaxe", sound="metal",
      recipe=(["  I", " RI", "R I"], {"I": "minecraft:iron_ingot", "R": "minecraft:red_concrete"})))
# 噴水
add(F("fountain", "噴水", "Fountain", "basic", [
    b(0, 0, 0, 16, 1, 16, "s"), b(0, 1, 0, 16, 5, 1.5, "s"), b(0, 1, 14.5, 16, 5, 16, "s"), b(0, 1, 1.5, 1.5, 5, 14.5, "s"), b(14.5, 1, 1.5, 16, 5, 14.5, "s"),
    b(1.5, 3.5, 1.5, 14.5, 4, 14.5, "w", shape=False), b(6.5, 1, 6.5, 9.5, 10, 9.5, "s"), b(4.5, 10, 4.5, 11.5, 11, 11.5, "s"),
    b(5, 10.6, 5, 11, 10.9, 11, "w", shape=False), b(7.3, 11, 7.3, 8.7, 13, 8.7, "s")],
    {"s": "minecraft:block/smooth_stone", "w": "jsn_furniture:block/water"}, particles="fountain", tool="pickaxe", sound="stone",
    recipe=(["SWS", "S S", "SSS"], {"S": "minecraft:smooth_stone", "W": "minecraft:water_bucket"})))
# 花壇
for fid, fja, fen, flowers_, item in (("red", "赤い花の花壇", "Red Flower Bed", ["poppy", "red_tulip", "poppy"], "minecraft:poppy"),
                                      ("yellow", "黄色い花の花壇", "Yellow Flower Bed", ["dandelion", "dandelion", "dandelion"], "minecraft:dandelion"),
                                      ("tulip", "チューリップの花壇", "Tulip Bed", ["red_tulip", "orange_tulip", "pink_tulip"], "minecraft:pink_tulip"),
                                      ("sunflower", "ひまわりの花壇", "Sunflower Bed", ["sunflower_front", "sunflower_front", "sunflower_front"], "minecraft:sunflower"),
                                      ("mix", "ミックスの花壇", "Mixed Flower Bed", ["cornflower", "allium", "oxeye_daisy"], "minecraft:allium")):
    els = [b(0, 0, 0, 16, 6, 16, {"up": "d", "down": "b", "north": "b", "south": "b", "east": "b", "west": "b"})]
    tx = {"b": "minecraft:block/bricks", "d": "minecraft:block/dirt"}
    for i, (x, z) in enumerate(((4, 4), (12, 7), (6, 12))):
        k = f"f{i}"
        tx[k] = f"minecraft:block/{flowers_[i]}"
        size = 7 if fid != "sunflower" else 9
        els += cross(x - size / 2, 6, x + size / 2, 6 + size + (3 if fid == "sunflower" else 0), k, z=z)
    add(F(f"flower_bed_{fid}", fja, fen, "basic", els, tx, tool="pickaxe", sound="stone",
          recipe=(["FFF", "BDB"], {"F": item, "B": "minecraft:bricks", "D": "minecraft:dirt"})))
add(F("garden_table", "ガーデンテーブル", "Garden Table", "basic", [
    b(1, 14, 1, 15, 15, 15, "w"), b(7, 1, 7, 9, 14, 9, "w"), b(3, 0, 7, 13, 1, 9, "w"), b(7, 0, 3, 9, 1, 13, "w"), b(7.5, 15, 7.5, 8.5, 16, 8.5, "w")],
    {"w": WHITE_C}, tool="pickaxe", sound="metal", recipe=(["III", " I ", "I I"], {"I": "minecraft:iron_nugget"})))
add(F("garden_chair", "ガーデンチェア", "Garden Chair", "seat", [
    b(3, 0, 3, 4, 8, 4, "w"), b(12, 0, 3, 13, 8, 4, "w"), b(3, 0, 12, 4, 8, 13, "w"), b(12, 0, 12, 13, 8, 13, "w"), b(3, 8, 3, 13, 9, 13, "w"),
    b(3, 9, 12, 4, 20, 13, "w", shape=False), b(12, 9, 12, 13, 20, 13, "w", shape=False), b(4, 12, 12.3, 12, 19, 12.7, "w", shape=False)],
    {"w": WHITE_C}, seat=9, tool="pickaxe", sound="metal", recipe=(["I  ", "III", "I I"], {"I": "minecraft:iron_nugget"}), count=2))

# 動く家具
add(F("ceiling_fan", "シーリングファン", "Ceiling Fan", "lamp", [b(7, 13, 7, 9, 16, 9, "k"), b(6, 10, 6, 10, 13, 10, "k"), b(6.5, 9, 6.5, 9.5, 10, 9.5, "g")],
      {"k": "minecraft:block/dark_oak_planks", "g": "jsn_furniture:block/lamp_shade", "b": "minecraft:block/stripped_dark_oak_log"},
      parts={"anim": [b(0, 11, 7, 6, 11.5, 9, "b"), b(10, 11, 7, 16, 11.5, 9, "b"), b(7, 11, 0, 9, 11.5, 6, "b"), b(7, 11, 10, 9, 11.5, 16, "b")]},
      anim="fan", light=12, hanging=True, sound="wood",
      recipe=(["PIP", " G "], {"P": "#minecraft:planks", "I": "minecraft:iron_ingot", "G": "minecraft:glowstone_dust"})))
add(F("grandfather_clock", "柱時計", "Grandfather Clock", "basic", [
    b(2, 0, 3, 14, 31, 14, "w"), b(1.5, 31, 2.5, 14.5, 32, 14.5, "w"), b(4, 22, 2.8, 12, 30, 3, "c"), b(4, 4, 2.8, 12, 20, 3, "g")],
    {"w": "minecraft:block/dark_oak_planks", "c": "jsn_furniture:block/clock_face", "g": "jsn_furniture:block/clock_glass", "h": "minecraft:block/black_concrete", "o": "minecraft:block/gold_block"},
    parts={"hour": [b(7.6, 26, 2.5, 8.4, 28.5, 2.7, "h")], "min": [b(7.7, 26, 2.3, 8.3, 29.5, 2.5, "h")],
           "pendulum": [b(7.7, 8, 3.2, 8.3, 20, 3.4, "o"), b(6.5, 6, 3.1, 9.5, 9, 3.5, "o")]},
    anim="grandfather", tall=True, recipe=(["PCP", "PGP", "PPP"], {"P": "minecraft:dark_oak_planks", "C": "minecraft:clock", "G": "minecraft:gold_ingot"})))
for w, wja, wen in WOODS:
    T = wood_tex(w)
    chair_els = [b(2, 0, 1, 3, 1.5, 15, "s"), b(13, 0, 1, 14, 1.5, 15, "s"), b(3, 1, 4, 4, 7, 5, "s"), b(12, 1, 4, 13, 7, 5, "s"), b(3, 1, 11, 4, 7, 12, "s"), b(12, 1, 11, 13, 7, 12, "s"),
                 b(2, 7, 3, 14, 9, 13, "p"), b(2.5, 9, 12, 3.5, 22, 13, "s"), b(12.5, 9, 12, 13.5, 22, 13, "s"), b(3.5, 12, 12.3, 12.5, 21, 12.7, "p"),
                 b(2, 11, 4, 3, 12, 12, "s"), b(13, 11, 4, 14, 12, 12, "s")]
    add(F(f"{w}_rocking_chair", f"{wja}のロッキングチェア", f"{wen} Rocking Chair", "seat", chair_els, {"p": T["p"], "s": T["s"]},
          static=[], parts={"anim": chair_els}, anim="rocker", seat=9,
          recipe=(["  S", "PPP", "C C"], {"S": "minecraft:stick", "P": wood_items(w)["P"], "C": wood_items(w)["H"]})))
add(F("washing_machine", "洗濯機", "Washing Machine", "lamp", [
    b(1, 0, 2, 15, 15, 15, "w"), b(1, 15, 2, 15, 16, 15, "t"), b(3, 2, 1.6, 13, 12, 2, "r", shape=False), b(10, 13, 1.6, 13, 14.5, 2, "k", shape=False)],
    {"w": WHITE_C, "t": "minecraft:block/light_gray_concrete", "r": "jsn_furniture:block/washer_ring", "k": "minecraft:block/black_concrete", "d": "jsn_furniture:block/washer_drum"},
    parts={"anim": [b(4, 3, 1.4, 12, 11, 1.6, "d")]}, anim="washer", light=0, tool="pickaxe", sound="metal",
    recipe=(["III", "IWI", "III"], {"I": "minecraft:iron_ingot", "W": "minecraft:water_bucket"})))
TV_ON = lambda: [b(2, 4, 6.8, 14, 13, 7, "o", shape=False)]
add(F("tv", "テレビ", "TV", "lamp", [b(5, 0, 6, 11, 1, 11, "k"), b(7, 1, 8, 9, 3, 9, "k"), b(1, 3, 7, 15, 14, 9, "k"), b(2, 4, 6.9, 14, 13, 7, "s", shape=False)],
      {"k": "minecraft:block/black_concrete", "s": "jsn_furniture:block/tv_off", "o": "jsn_furniture:block/tv_on"}, on=TV_ON, light=7, tool="pickaxe", sound="metal",
      recipe=(["III", "IGI", " R "], {"I": "minecraft:iron_ingot", "G": "minecraft:glass_pane", "R": "minecraft:redstone"})))
add(F("game_console", "ゲーム機", "Game Console", "basic", [b(3, 0, 4, 13, 2, 12, "c"), b(4, 0, 1, 7, 1, 3, "p"), b(9, 0, 1, 12, 1, 3, "p"), b(5.5, 0.5, 2, 10.5, 0.8, 2.5, "k")],
      {"c": "jsn_furniture:block/console_top", "p": "minecraft:block/gray_concrete", "k": "minecraft:block/black_concrete"}, tool="pickaxe", sound="metal",
      recipe=(["IRI", "B B"], {"I": "minecraft:iron_ingot", "R": "minecraft:redstone", "B": "minecraft:stone_button"})))

# 遊び・趣味
add(F("piano", "ピアノ", "Piano", "instrument", [
    b(0, 0, 8, 16, 16, 16, "k"), b(0, 7, 2, 16, 8, 8, "k"), b(0.5, 8, 2.5, 15.5, 9, 7.5, {"up": "y", "north": "k", "south": "k", "east": "k", "west": "k", "down": "k"},
                                                            uv={"up": [0, 0, 16, 16]}), b(1, 0, 3, 2, 7, 4, "k"), b(14, 0, 3, 15, 7, 4, "k")],
    {"k": "minecraft:block/black_concrete", "y": "jsn_furniture:block/piano_keys"}, instrument="piano", tool="pickaxe", sound="wood",
    recipe=(["PPP", "PNP", "IWI"], {"P": "minecraft:black_concrete", "N": "minecraft:note_block", "I": "minecraft:iron_ingot", "W": "minecraft:white_concrete"})))
add(F("xylophone", "木琴", "Xylophone", "instrument", [b(1, 0, 3, 2, 8, 4, "l"), b(14, 0, 3, 15, 8, 4, "l"), b(1, 0, 12, 2, 8, 13, "l"), b(14, 0, 12, 15, 8, 13, "l"),
                                                         b(0, 8, 3, 16, 9, 13, {"up": "x", "north": "l", "south": "l", "east": "l", "west": "l", "down": "l"}, uv={"up": [0, 0, 16, 16]})],
      {"l": "minecraft:block/dark_oak_planks", "x": "jsn_furniture:block/xylophone"}, instrument="xylophone",
      recipe=(["BBB", "S S"], {"B": "minecraft:bone_block", "S": "minecraft:stick"})))
add(F("guitar", "ギター", "Guitar", "instrument", [
    b(5, 0, 6, 11, 2, 10, "k"), b(4.5, 1, 7, 11.5, 9, 9, {"north": "g", "south": "w", "east": "w", "west": "w", "up": "w", "down": "w"}, uv={"north": [0, 0, 16, 16]}),
    b(7, 9, 7.5, 9, 20, 8.5, "n", shape=False), b(6.5, 20, 7.3, 9.5, 23, 8.7, "n", shape=False)],
    {"k": "minecraft:block/black_concrete", "g": "jsn_furniture:block/guitar_front", "w": "minecraft:block/orange_terracotta", "n": "minecraft:block/dark_oak_planks"},
    instrument="guitar", recipe=(["  S", "PS ", "PP "], {"S": "minecraft:string", "P": "#minecraft:planks"})))
add(F("taiko", "和太鼓", "Taiko Drum", "instrument", [
    b(2, 0, 2, 14, 2, 14, "s"), b(3, 2, 3, 13, 14, 13, {"up": "t", "down": "t", "north": "w", "south": "w", "east": "w", "west": "w"}, uv={"up": [0, 0, 16, 16]}),
    b(2.5, 3, 2.5, 13.5, 4, 13.5, "r", shape=False), b(2.5, 12, 2.5, 13.5, 13, 13.5, "r", shape=False)],
    {"s": "minecraft:block/dark_oak_planks", "t": "jsn_furniture:block/taiko_skin", "w": "minecraft:block/stripped_spruce_log", "r": "minecraft:block/gold_block"},
    instrument="taiko", tab="wa", recipe=(["LLL", "WNW", "WWW"], {"L": "minecraft:leather", "W": "minecraft:stripped_spruce_log", "N": "minecraft:note_block"})))
add(F("darts", "ダーツ", "Dartboard", "darts", [b(1, 1, 15, 15, 15, 16, {"north": "d", "south": "k", "east": "k", "west": "k", "up": "k", "down": "k"}, uv={"north": [0, 0, 16, 16]})],
      {"d": "jsn_furniture:block/darts", "k": "minecraft:block/black_concrete"}, wall=True,
      recipe=(["RWR", "WAW", "RWR"], {"R": "minecraft:red_dye", "W": "minecraft:white_wool", "A": "minecraft:arrow"})))
for bid, bja, ben, item, tab in (("shogi", "将棋盤", "Shogi Board", "minecraft:flint", "wa"), ("go", "碁盤", "Go Board", "minecraft:white_dye", "wa"),
                                 ("chess", "チェス盤", "Chess Board", "minecraft:black_dye", "west")):
    els = [b(1, 0, 1, 15, 1, 15, {"up": "t", "down": "w", "north": "w", "south": "w", "east": "w", "west": "w"}, uv={"up": [0, 0, 16, 16]})]
    if bid in ("shogi", "go"):
        els = [b(1, 3, 1, 15, 6, 15, {"up": "t", "down": "w", "north": "w", "south": "w", "east": "w", "west": "w"}, uv={"up": [0, 0, 16, 16]}),
               b(2, 0, 2, 4, 3, 4, "w"), b(12, 0, 2, 14, 3, 4, "w"), b(2, 0, 12, 4, 3, 14, "w"), b(12, 0, 12, 14, 3, 14, "w")]
    add(F(f"{bid}_board", bja, ben, "basic", els, {"t": f"jsn_furniture:block/board_{bid}", "w": "minecraft:block/stripped_oak_log"}, tab=tab,
          recipe=(["X", "P"], {"X": item, "P": "minecraft:oak_pressure_plate"})))
add(F("telescope", "望遠鏡", "Telescope", "basic", [
    b(7.5, 0, 3, 8.5, 12, 4, "k"), b(3, 0, 12, 4, 12, 13, "k"), b(12, 0, 12, 13, 12, 13, "k"), b(7, 12, 7, 9, 13, 9, "k"),
    b(6.5, 12, 1, 9.5, 15, 15, "b", shape=False, rot={"origin": [8, 13.5, 8], "axis": "x", "angle": 22.5})],
    {"k": "minecraft:block/black_concrete", "b": "minecraft:block/gold_block"}, tool="pickaxe", sound="metal",
    recipe=(["  G", " C ", "S S"], {"G": "minecraft:glass_pane", "C": "minecraft:copper_ingot", "S": "minecraft:stick"})))
for w, wja, wen in WOODS:
    T = wood_tex(w)
    add(F(f"{w}_bookshelf", f"{wja}の本棚", f"{wen} Bookshelf", "storage", [
        b(0, 0, 4, 16, 16, 16, {"north": "b", "south": "p", "east": "p", "west": "p", "up": "p", "down": "p"}, uv={"north": [0, 0, 16, 16]}),
        b(0, 0, 3, 16, 1, 4, "p"), b(0, 15, 3, 16, 16, 4, "p"), b(0, 1, 3, 1, 15, 4, "p"), b(15, 1, 3, 16, 15, 4, "p"), b(1, 7.5, 3, 15, 8.5, 4, "p")],
        {"p": T["p"], "b": "minecraft:block/bookshelf"}, rows=3,
        recipe=(["PPP", "BCB", "PPP"], {"P": wood_items(w)["H"], "B": "minecraft:book", "C": "minecraft:chest"})))

# お店・屋台（屋根が上のマスまでのびる）


def yatai(top_tex):
    return [b(0, 0, 2, 16, 13, 16, "w"), b(-0.5, 13, 0, 16.5, 14, 16, "c"), b(0.5, 14, 1, 15.5, 14.5, 15, "f", shape=False),
            b(0, 13, 14, 1, 28, 16, "w"), b(15, 13, 14, 16, 28, 16, "w"), b(0, 13, 0, 1, 28, 2, "w", shape=False), b(15, 13, 0, 16, 28, 2, "w", shape=False),
            b(-1, 28, -1, 17, 29, 17, "r", shape=False), b(0, 22, 0.5, 16, 28, 1, "n", shape=False)]


for sid, sja, sen, food, noren, item in (("takoyaki", "たこ焼きの屋台", "Takoyaki Stall", "takoyaki", "noren_takoyaki", "minecraft:wheat"),
                                         ("ringoame", "りんご飴の屋台", "Candy Apple Stall", "ringoame", "noren_ringoame", "minecraft:apple"),
                                         ("yakisoba", "焼きそばの屋台", "Yakisoba Stall", "yakisoba", "noren_yakisoba", "minecraft:carrot"),
                                         ("kakigori", "かき氷の屋台", "Shaved Ice Stall", "kakigori", "noren_kakigori", "minecraft:ice"),
                                         ("kingyo", "金魚すくいの屋台", "Goldfish Scooping Stall", "kingyo", "noren_kingyo", "minecraft:tropical_fish")):
    add(F(f"yatai_{sid}", sja, sen, "storage", yatai(food),
          {"w": "minecraft:block/stripped_spruce_log", "c": "minecraft:block/spruce_planks", "f": f"jsn_furniture:block/food_{food}",
           "r": "minecraft:block/red_wool" if sid != "kakigori" else "minecraft:block/light_blue_wool", "n": f"jsn_furniture:block/{noren}"},
          rows=2, tab="wa", particles="steam" if sid in ("takoyaki", "yakisoba") else "",
          recipe=(["RRR", "SXS", "PCP"], {"R": "minecraft:red_wool", "S": "minecraft:stick", "X": item, "P": "minecraft:spruce_planks", "C": "minecraft:chest"})))
for c in ("red", "blue", "green", "yellow"):
    cja = {"red": "赤", "blue": "青", "green": "緑", "yellow": "黄色"}[c]
    add(F(f"{c}_roten", f"{cja}い露店" if c != "green" else "緑の露店", f"{c.title()} Market Stall", "storage", [
        b(0, 0, 4, 16, 10, 16, "w"), b(0, 10, 3, 16, 11, 16, "p"), b(0, 11, 14, 1, 26, 16, "w"), b(15, 11, 14, 16, 26, 16, "w"),
        b(-1, 26, 2, 17, 27, 17, "c", shape=False), b(-1, 25, 0, 17, 26, 2, "c", shape=False), b(-1, 23, -1, 17, 25, 0, "c", shape=False)],
        {"w": "minecraft:block/oak_planks", "p": "minecraft:block/stripped_oak_log", "c": f"jsn_furniture:block/awning_{c}"}, rows=2,
        recipe=(["WWW", "S S", "PCP"], {"W": f"minecraft:{c}_wool", "S": "minecraft:stick", "P": "#minecraft:planks", "C": "minecraft:chest"})))
add(F("coffee_machine", "コーヒーマシン", "Coffee Machine", "basic", [
    b(4, 0, 4, 12, 1, 12, "k"), b(4, 1, 9, 12, 13, 13, "m"), b(4, 10, 4, 12, 13, 9, "m"), b(6.5, 1, 5.5, 9.5, 4, 8.5, "c"), b(7.5, 9, 6.5, 8.5, 10, 7.5, "k")],
    {"k": "minecraft:block/black_concrete", "m": "minecraft:block/iron_block", "c": "jsn_furniture:block/coffee_cup"}, particles="steam", tool="pickaxe", sound="metal",
    recipe=(["III", "IBI", "I I"], {"I": "minecraft:iron_ingot", "B": "minecraft:cocoa_beans"})))
add(F("cake_case", "ケーキのショーケース", "Cake Display Case", "storage", [
    b(0, 0, 1, 16, 6, 16, "w"), b(0.5, 6, 1.5, 15.5, 15, 15.5, "g"), b(0, 15, 1, 16, 16, 16, "w"),
    b(2, 7, 3, 6, 9, 7, "k", shape=False), b(7, 7, 3, 11, 9, 7, "s", shape=False), b(12, 7, 3, 15, 9, 7, "k", shape=False),
    b(2, 11, 9, 6, 13, 13, "s", shape=False), b(7, 11, 9, 11, 13, 13, "k", shape=False), b(1, 10, 2, 15, 10.5, 15, "w", shape=False)],
    {"w": WHITE_C, "g": "jsn_furniture:block/case_glass", "k": "jsn_furniture:block/cake_short", "s": "jsn_furniture:block/cake_choco"}, rows=1,
    recipe=(["GGG", "GCG", "QQQ"], {"G": "minecraft:glass", "C": "minecraft:cake", "Q": "minecraft:quartz_block"})))
add(F("vending_machine", "自動販売機", "Vending Machine", "storage", [
    b(1, 0, 3, 15, 31, 15, "r"), b(2, 14, 2.6, 14, 29, 3, "d", shape=False), b(2, 3, 2.6, 14, 6, 3, "k", shape=False), b(12, 9, 2.6, 13.5, 12, 3, "m", shape=False)],
    {"r": RED_C, "d": "jsn_furniture:block/vending_drinks", "k": "minecraft:block/black_concrete", "m": "minecraft:block/iron_block"},
    tall=True, rows=3, light=10, tool="pickaxe", sound="metal",
    recipe=(["IRI", "IGI", "ICI"], {"I": "minecraft:iron_ingot", "R": "minecraft:red_dye", "G": "minecraft:glass_pane", "C": "minecraft:chest"})))


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
    if lk == "animal":
        return
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


def make_animal_textures():
    def fur(name, rgb, seed, patches=None):
        im = Image.new("RGBA", (16, 16)); noise_fill(im, rgb, 6, seed)
        if patches:
            d = ImageDraw.Draw(im)
            for (x, y, r, c) in patches:
                d.ellipse([x - r, y - r, x + r, y + r], fill=c)
        save(im, f"block/fur_{name}")
        return im

    for i, (k, (rgb, face, ear)) in enumerate(ANIMAL.items()):
        patches = {"cat_calico": [(4, 4, 3, (225, 130, 50, 255)), (12, 11, 3, (40, 35, 35, 255))],
                   "cow": [(3, 4, 3, (35, 30, 30, 255)), (12, 10, 4, (35, 30, 30, 255)), (5, 13, 2, (35, 30, 30, 255))]}.get(k)
        im = fur(k, rgb, 40 + i, patches)
        if k == "bee":
            d = ImageDraw.Draw(im)
            for y0 in (3, 9):
                d.rectangle([0, y0, 15, y0 + 2], fill=(40, 30, 20, 255))
            save(im, "block/fur_bee")
    fur("axolotl_gill", (215, 80, 120), 92)
    fur("turtle_shell", (60, 110, 55), 93, [(4, 4, 2, (80, 130, 60, 255)), (11, 5, 2, (80, 130, 60, 255)), (8, 11, 2, (80, 130, 60, 255))])
    im = Image.new("RGBA", (16, 16), (230, 245, 255, 150)); ImageDraw.Draw(im).rectangle([0, 0, 15, 15], outline=(255, 255, 255, 200)); save(im, "block/wing")
    fur("black", (35, 35, 40), 90)
    fur("white", (245, 245, 245), 91)

    def face(name, rgb, style):
        im = Image.new("RGBA", (16, 16)); noise_fill(im, rgb, 4, hash(name) & 255); d = ImageDraw.Draw(im)
        dark = (30, 25, 25, 255)
        if style in ("cat", "cat_black", "maneki", "maneki_gold"):
            if style == "cat_black":
                eye = (240, 210, 60, 255)
                d.rectangle([3, 6, 5, 8], fill=eye); d.rectangle([10, 6, 12, 8], fill=eye)
                d.point([(4, 7), (11, 7)], fill=dark)
            elif style.startswith("maneki"):
                d.line([(3, 8), (4, 7), (5, 8)], fill=dark); d.line([(10, 8), (11, 7), (12, 8)], fill=dark)
                d.rectangle([2, 0, 4, 2], fill=(220, 90, 100, 255)); d.rectangle([11, 0, 13, 2], fill=(220, 90, 100, 255))
                d.point([(2, 10), (3, 11)], fill=(240, 140, 150, 255)); d.point([(13, 10), (12, 11)], fill=(240, 140, 150, 255))
            else:
                d.rectangle([3, 6, 5, 8], fill=(80, 150, 210, 255)); d.rectangle([10, 6, 12, 8], fill=(80, 150, 210, 255))
                d.rectangle([4, 6, 4, 8], fill=dark); d.rectangle([11, 6, 11, 8], fill=dark)
            d.rectangle([7, 9, 8, 9], fill=(235, 140, 150, 255))
            d.line([(6, 11), (7, 12), (8, 11), (9, 12)], fill=dark if style != "cat_black" else (200, 200, 200, 255))
            if style != "cat_black":
                d.line([(0, 10), (3, 10)], fill=(120, 120, 120, 255)); d.line([(12, 10), (15, 10)], fill=(120, 120, 120, 255))
        elif style == "fox" or style == "kitsune":
            d.polygon([(3, 9), (8, 15), (12, 9)], fill=(250, 245, 240, 255) if style == "fox" else (200, 30, 30, 255))
            if style == "kitsune":
                d.line([(3, 6), (6, 7)], fill=(200, 30, 30, 255)); d.line([(12, 6), (9, 7)], fill=(200, 30, 30, 255))
            else:
                d.rectangle([3, 6, 5, 7], fill=dark); d.rectangle([10, 6, 12, 7], fill=dark)
            d.rectangle([7, 12, 8, 13], fill=dark)
        elif style == "rabbit":
            d.rectangle([3, 6, 5, 8], fill=(200, 50, 70, 255)); d.rectangle([10, 6, 12, 8], fill=(200, 50, 70, 255))
            d.point((7, 10), fill=(240, 150, 160, 255)); d.point((8, 10), fill=(240, 150, 160, 255)); d.line([(6, 12), (7, 11), (8, 11), (9, 12)], fill=dark)
        elif style == "tanuki":
            d.ellipse([1, 4, 7, 10], fill=(60, 45, 35, 255)); d.ellipse([8, 4, 14, 10], fill=(60, 45, 35, 255))
            d.rectangle([3, 6, 4, 7], fill=(250, 250, 250, 255)); d.rectangle([10, 6, 11, 7], fill=(250, 250, 250, 255))
            d.ellipse([5, 9, 10, 14], fill=(225, 210, 190, 255)); d.rectangle([7, 10, 8, 11], fill=dark)
        elif style == "shiba":
            d.ellipse([3, 8, 12, 15], fill=(250, 245, 235, 255)); d.rectangle([3, 6, 4, 7], fill=dark); d.rectangle([11, 6, 12, 7], fill=dark)
            d.rectangle([7, 10, 8, 11], fill=dark); d.line([(6, 13), (7, 13), (8, 13), (9, 13)], fill=(200, 80, 80, 255))
        elif style == "bear":
            d.ellipse([4, 8, 11, 14], fill=(200, 165, 120, 255)); d.rectangle([3, 6, 4, 7], fill=dark); d.rectangle([11, 6, 12, 7], fill=dark)
            d.rectangle([7, 9, 8, 10], fill=dark)
        elif style == "panda":
            d.ellipse([1, 5, 6, 10], fill=dark); d.ellipse([9, 5, 14, 10], fill=dark)
            d.point([(4, 7), (10, 7)], fill=(250, 250, 250, 255)); d.rectangle([7, 10, 8, 11], fill=dark)
        elif style == "penguin":
            d.ellipse([2, 3, 13, 15], fill=(245, 245, 245, 255)); d.rectangle([4, 5, 5, 6], fill=dark); d.rectangle([10, 5, 11, 6], fill=dark)
            d.polygon([(6, 8), (9, 8), (7.5, 10)], fill=(240, 150, 40, 255))
        elif style == "chick":
            d.rectangle([4, 5, 5, 6], fill=dark); d.rectangle([10, 5, 11, 6], fill=dark); d.polygon([(6, 8), (9, 8), (7.5, 10)], fill=(240, 120, 30, 255))
            d.point([(3, 9), (12, 9)], fill=(250, 160, 140, 255))
        elif style in ("wolf", "polar_bear"):
            d.ellipse([4, 8, 11, 15], fill=(240, 240, 240, 255) if style == "wolf" else (250, 250, 248, 255))
            d.rectangle([3, 5, 4, 6], fill=dark); d.rectangle([11, 5, 12, 6], fill=dark); d.rectangle([6, 9, 9, 10], fill=dark)
            if style == "wolf":
                d.line([(2, 4), (5, 5)], fill=(150, 150, 155, 255)); d.line([(13, 4), (10, 5)], fill=(150, 150, 155, 255))
        elif style == "axolotl":
            d.rectangle([2, 6, 3, 7], fill=dark); d.rectangle([12, 6, 13, 7], fill=dark); d.arc([5, 7, 10, 11], 20, 160, fill=(150, 60, 90, 255))
            d.point([(3, 9), (12, 9)], fill=(250, 120, 150, 255))
        elif style == "frog":
            d.line([(2, 9), (13, 9)], fill=(60, 80, 40, 255)); d.arc([3, 5, 12, 11], 20, 160, fill=(60, 80, 40, 255))
            d.point([(4, 11), (11, 11)], fill=(230, 150, 120, 255))
        elif style == "bee":
            d.rectangle([0, 0, 15, 15], fill=(245, 200, 60, 255))
            d.rectangle([2, 5, 5, 10], fill=dark); d.rectangle([10, 5, 13, 10], fill=dark)
            d.point([(3, 6), (11, 6)], fill=(255, 255, 255, 255)); d.rectangle([6, 12, 9, 12], fill=(90, 60, 20, 255))
        elif style == "sheep":
            d.rectangle([0, 0, 15, 15], fill=(225, 205, 180, 255)); d.rectangle([0, 0, 15, 3], fill=(250, 250, 250, 255))
            d.rectangle([3, 6, 4, 7], fill=dark); d.rectangle([11, 6, 12, 7], fill=dark); d.rectangle([6, 10, 9, 11], fill=(230, 160, 160, 255))
        elif style == "pig":
            d.rectangle([3, 5, 4, 6], fill=dark); d.rectangle([11, 5, 12, 6], fill=dark)
            d.rectangle([5, 8, 10, 12], fill=(250, 190, 195, 255)); d.rectangle([6, 9, 6, 10], fill=(150, 80, 90, 255)); d.rectangle([9, 9, 9, 10], fill=(150, 80, 90, 255))
        elif style == "cow":
            d.rectangle([0, 0, 6, 5], fill=(35, 30, 30, 255)); d.rectangle([3, 6, 4, 7], fill=dark); d.rectangle([11, 6, 12, 7], fill=dark)
            d.rectangle([4, 10, 11, 14], fill=(240, 180, 175, 255)); d.point([(6, 12), (9, 12)], fill=(120, 70, 70, 255))
        elif style == "chicken":
            d.rectangle([3, 5, 4, 6], fill=dark); d.rectangle([11, 5, 12, 6], fill=dark)
            d.rectangle([6, 7, 9, 9], fill=(240, 160, 40, 255)); d.rectangle([7, 10, 8, 12], fill=(220, 40, 40, 255))
        elif style == "parrot":
            d.ellipse([1, 3, 6, 8], fill=(250, 250, 250, 255)); d.ellipse([9, 3, 14, 8], fill=(250, 250, 250, 255))
            d.point([(4, 5), (11, 5)], fill=dark); d.polygon([(6, 8), (9, 8), (8, 13)], fill=(250, 200, 40, 255))
        elif style == "turtle":
            d.rectangle([3, 5, 5, 7], fill=dark); d.rectangle([10, 5, 12, 7], fill=dark); d.arc([4, 8, 11, 12], 20, 160, fill=(40, 70, 40, 255))
        elif style == "allay":
            d.rectangle([2, 4, 13, 13], fill=(40, 100, 170, 255)); d.rectangle([4, 7, 5, 9], fill=(230, 250, 255, 255)); d.rectangle([10, 7, 11, 9], fill=(230, 250, 255, 255))
        elif style == "enaga":
            d.rectangle([4, 7, 4, 7], fill=dark); d.rectangle([11, 7, 11, 7], fill=dark)
            d.rectangle([7, 9, 8, 9], fill=dark); d.point([(2, 10), (13, 10)], fill=(250, 225, 225, 255))
        elif style == "capybara":
            d.rectangle([3, 4, 4, 5], fill=dark); d.rectangle([11, 4, 12, 5], fill=dark)
            d.rectangle([4, 8, 11, 15], fill=(110, 75, 50, 255)); d.rectangle([5, 9, 6, 10], fill=dark); d.rectangle([9, 9, 10, 10], fill=dark)
        elif style.startswith("daruma"):
            d.ellipse([2, 2, 13, 13], fill=(250, 245, 235, 255))
            d.ellipse([3, 5, 6, 8], fill=(250, 250, 250, 255), outline=dark); d.ellipse([9, 5, 12, 8], fill=(250, 250, 250, 255), outline=dark)
            d.point((4, 6), fill=dark)  # 片目だけ黒（願いをこめて）
            d.line([(3, 4), (6, 3)], fill=dark, width=1); d.line([(9, 3), (12, 4)], fill=dark)
            d.arc([4, 8, 11, 13], 20, 160, fill=dark)
            d.text((5, 14), "", fill=dark)
        save(im, f"block/face_{name}")

    for k, (rgb, style, ear) in ANIMAL.items():
        face(k, rgb, style)
    face("maneki", (238, 238, 236), "maneki")
    face("maneki_gold", (235, 190, 60), "maneki_gold")
    face("kitsune_statue", (128, 128, 128), "kitsune")
    face("daruma_red", (180, 30, 30), "daruma")
    face("daruma_white", (240, 240, 240), "daruma")
    # キャットタワーの麻ひも・犬小屋の札・えさ
    im = Image.new("RGBA", (16, 16)); noise_fill(im, (190, 160, 110), 8, 95); d = ImageDraw.Draw(im)
    for y in range(0, 16, 2):
        d.line([0, y, 15, y + 1], fill=(160, 130, 85, 255))
    save(im, "block/sisal")
    im = Image.new("RGBA", (16, 16), (240, 230, 200, 255)); d = ImageDraw.Draw(im); d.rectangle([0, 0, 15, 15], outline=(120, 80, 40, 255))
    d.ellipse([5, 7, 8, 10], fill=(90, 60, 40, 255))
    for x, y in ((4, 4), (7, 3), (10, 4), (11, 7)):
        d.ellipse([x - 1, y - 1, x + 1, y + 1], fill=(90, 60, 40, 255))
    save(im, "block/dog_house_sign")
    im = Image.new("RGBA", (16, 16)); noise_fill(im, (150, 95, 50), 25, 97); save(im, "block/pet_food")
    for c, cja, cen in COLORS:
        base = hx(DYE_RGB[c])
        im = Image.new("RGBA", (16, 16)); noise_fill(im, base, 5, 99); d = ImageDraw.Draw(im)
        pad = (250, 250, 250, 255) if c not in ("white", "light_gray", "yellow") else (120, 90, 80, 255)
        d.ellipse([5, 7, 10, 12], fill=pad)
        for x, y in ((4, 5), (7, 3), (10, 5)):
            d.ellipse([x - 1, y - 1, x + 1, y + 1], fill=pad)
        save(im, f"block/paw_rug_{c}")


def make_textures3():
    def new(rgb=(0, 0, 0, 0)):
        im = Image.new("RGBA", (16, 16), rgb); return im, ImageDraw.Draw(im)
    im, d = new((215, 230, 240, 90)); d.rectangle([0, 0, 15, 15], outline=(80, 60, 40, 255)); save(im, "block/clock_glass")
    im, d = new((0, 0, 0, 0)); d.ellipse([0, 0, 15, 15], outline=(180, 180, 190, 255), width=2); save(im, "block/washer_ring")
    im, d = new((0, 0, 0, 0)); d.ellipse([0, 0, 15, 15], fill=(120, 150, 180, 230))
    for x, y, c in ((5, 5, (230, 80, 80)), (10, 8, (80, 140, 230)), (6, 10, (240, 220, 90))):
        d.rectangle([x - 2, y - 1, x + 1, y + 1], fill=c + (255,))
    save(im, "block/washer_drum")
    im, d = new((20, 22, 28, 255)); d.line([2, 2, 5, 5], fill=(60, 70, 80, 255)); save(im, "block/tv_off")
    # テレビの画面：色が変わっていくアニメ
    frames = 8
    strip = Image.new("RGBA", (16, 16 * frames))
    rnd = random.Random(3)
    for f in range(frames):
        fr, dd = new((40 + f * 20, 120, 200 - f * 15, 255))
        dd.rectangle([0, 10, 15, 15], fill=(60, 160 - f * 5, 70, 255))
        dd.ellipse([2 + f, 4, 6 + f, 8], fill=(250, 220, 80, 255))
        for _ in range(5):
            dd.point((rnd.randint(0, 15), rnd.randint(0, 9)), fill=(255, 255, 255, 255))
        strip.paste(fr, (0, f * 16))
    save(strip, "block/tv_on")
    with open(f"{A}/textures/block/tv_on.png.mcmeta", "w") as fh:
        json.dump({"animation": {"frametime": 6, "interpolate": True}}, fh)
    im, d = new((235, 235, 240, 255)); d.rectangle([0, 0, 15, 15], outline=(160, 160, 170, 255)); d.ellipse([10, 5, 12, 7], fill=(60, 200, 90, 255)); save(im, "block/console_top")
    im, d = new((250, 250, 250, 255))
    for x in range(0, 16, 2):
        d.line([x, 0, x, 15], fill=(170, 170, 170, 255))
    for x in (1, 3, 7, 9, 11):
        d.rectangle([x, 0, x + 1, 8], fill=(25, 25, 25, 255))
    save(im, "block/piano_keys")
    im, d = new((0, 0, 0, 0))
    cols = [(230, 70, 70), (240, 150, 60), (240, 220, 70), (110, 200, 90), (80, 170, 230), (100, 110, 220), (170, 100, 210), (230, 110, 170)]
    for i, c in enumerate(cols):
        d.rectangle([i * 2, 1 + i // 2, i * 2 + 1, 14 - i // 2], fill=c + (255,))
    save(im, "block/xylophone")
    im, d = new((215, 140, 60, 255)); d.ellipse([3, 3, 12, 12], fill=(40, 25, 15, 255)); d.line([7, 0, 7, 15], fill=(230, 230, 230, 255)); d.line([8, 0, 8, 15], fill=(230, 230, 230, 255))
    save(im, "block/guitar_front")
    im, d = new((235, 220, 190, 255)); d.ellipse([0, 0, 15, 15], outline=(200, 180, 140, 255)); d.ellipse([5, 5, 10, 10], outline=(210, 60, 50, 255)); save(im, "block/taiko_skin")
    im, d = new((0, 0, 0, 0))
    for r, c in ((7.5, (30, 30, 30)), (6, (240, 230, 200)), (4.5, (200, 40, 40)), (3, (240, 230, 200)), (1.5, (40, 150, 60))):
        d.ellipse([7.5 - r, 7.5 - r, 7.5 + r, 7.5 + r], fill=c + (255,))
    d.point((7, 7), fill=(200, 40, 40, 255)); save(im, "block/darts")
    im, d = new((220, 180, 110, 255))
    for i in range(1, 16, 2):
        d.line([i, 0, i, 15], fill=(60, 40, 20, 255)); d.line([0, i, 15, i], fill=(60, 40, 20, 255))
    for x, y in ((2, 2), (6, 4), (10, 2), (12, 12), (4, 12)):
        d.polygon([(x, y), (x + 1, y - 1), (x + 2, y), (x + 2, y + 1), (x, y + 1)], fill=(240, 215, 160, 255))
    save(im, "block/board_shogi")
    im, d = new((220, 180, 110, 255))
    for i in range(1, 16, 2):
        d.line([i, 0, i, 15], fill=(50, 35, 20, 255)); d.line([0, i, 15, i], fill=(50, 35, 20, 255))
    for x, y, c in ((3, 3, 0), (5, 7, 255), (9, 9, 0), (11, 5, 255), (7, 13, 0)):
        d.ellipse([x - 1, y - 1, x + 1, y + 1], fill=(c, c, c, 255))
    save(im, "block/board_go")
    im, d = new((240, 220, 180, 255))
    for y in range(0, 16, 2):
        for x in range(0, 16, 2):
            if (x + y) // 2 % 2:
                d.rectangle([x, y, x + 1, y + 1], fill=(110, 70, 40, 255))
    save(im, "block/board_chess")
    # 屋台の食べ物
    im, d = new((60, 60, 65, 255))
    for x in range(1, 16, 4):
        for y in range(1, 16, 4):
            d.ellipse([x, y, x + 2, y + 2], fill=(200, 140, 60, 255)); d.point((x + 1, y), fill=(60, 40, 20, 255))
    save(im, "block/food_takoyaki")
    im, d = new((230, 220, 200, 255))
    for x, y in ((2, 2), (8, 3), (4, 9), (11, 10)):
        d.ellipse([x, y, x + 3, y + 3], fill=(220, 30, 40, 255)); d.point((x + 1, y + 1), fill=(255, 200, 200, 255))
    save(im, "block/food_ringoame")
    im, d = new((60, 60, 65, 255))
    for i in range(30):
        x = random.Random(i).randint(0, 14); y = random.Random(i + 99).randint(0, 14)
        d.line([x, y, x + 2, y + 1], fill=(200, 150, 80, 255))
    d.point([(4, 4), (10, 6), (6, 11)], fill=(80, 160, 70, 255)); save(im, "block/food_yakisoba")
    im, d = new((230, 230, 235, 255))
    for x, c in ((2, (230, 60, 80)), (7, (60, 180, 220)), (12, (240, 200, 60))):
        d.ellipse([x - 2, 4, x + 2, 9], fill=(250, 250, 255, 255)); d.ellipse([x - 2, 4, x + 2, 7], fill=c + (255,))
    save(im, "block/food_kakigori")
    im, d = new((70, 130, 210, 255))
    for x, y in ((3, 4), (10, 3), (6, 10), (12, 11)):
        d.ellipse([x, y, x + 2, y + 1], fill=(240, 80, 40, 255)); d.point((x + 3, y), fill=(240, 120, 60, 255))
    save(im, "block/food_kingyo")
    for name, bg, fg in (("takoyaki", (200, 40, 40), (255, 255, 255)), ("ringoame", (240, 240, 240), (200, 30, 40)), ("yakisoba", (230, 120, 30), (40, 30, 20)),
                         ("kakigori", (250, 250, 255), (40, 90, 200)), ("kingyo", (250, 250, 255), (230, 70, 40))):
        im, d = new(bg + (255,))
        for x in range(0, 16, 4):
            d.line([x, 0, x, 15], fill=shade(bg + (255,), 0.85))
        if name == "kakigori":
            d.text((4, 2), "氷", fill=(200, 40, 40, 255))
        d.ellipse([5, 4, 10, 9], fill=fg + (255,))
        save(im, f"block/noren_{name}")
    for c in ("red", "blue", "green", "yellow"):
        im, d = new((0, 0, 0, 0))
        for x in range(16):
            d.line([x, 0, x, 15], fill=hx(DYE_RGB[c]) if (x // 2) % 2 == 0 else (245, 245, 245, 255))
        save(im, f"block/awning_{c}")
    im, d = new((250, 250, 250, 255)); d.rectangle([2, 2, 13, 5], fill=(110, 70, 40, 255)); save(im, "block/coffee_cup")
    im, d = new((250, 245, 235, 255)); d.rectangle([0, 0, 15, 3], fill=(250, 250, 250, 255)); d.rectangle([0, 7, 15, 8], fill=(240, 150, 160, 255)); d.ellipse([6, 0, 9, 3], fill=(220, 30, 40, 255))
    save(im, "block/cake_short")
    im, d = new((110, 65, 40, 255)); d.rectangle([0, 0, 15, 3], fill=(80, 45, 25, 255)); d.rectangle([0, 8, 15, 9], fill=(150, 100, 70, 255)); save(im, "block/cake_choco")
    im, d = new((240, 245, 250, 255))
    for row, y in enumerate((1, 6, 11)):
        for i, x in enumerate(range(1, 15, 3)):
            c = [(220, 50, 50), (60, 120, 220), (240, 180, 40), (70, 170, 80), (160, 90, 200)][(i + row) % 5]
            d.rectangle([x, y, x + 1, y + 3], fill=c + (255,)); d.point((x, y + 4), fill=(60, 200, 90, 255))
    save(im, "block/vending_drinks")
    # 時計：針は別のモデルで動かすので、文字盤だけ
    im, d = new((245, 240, 225, 255)); d.ellipse([0, 0, 15, 15], outline=(60, 40, 20, 255))
    for a in range(12):
        r = math.radians(a * 30)
        d.point((round(7.5 + math.cos(r) * 6), round(7.5 + math.sin(r) * 6)), fill=(30, 30, 30, 255))
    save(im, "block/clock_face")


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
    # 水（バニラの水の絵は色をつけて使う前提なので、青い水を用意）
    im = Image.new("RGBA", (16, 16)); noise_fill(im, (60, 110, 210), 10, 35); d = ImageDraw.Draw(im)
    for y in (3, 9, 14):
        d.line([(1, y), (5, y - 1), (9, y)], fill=(140, 180, 240, 255))
    save(im, "block/water")
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
    base_els = fur.els if fur.static is None else fur.static
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
    item_els = fur.els + (fur.body or []) + [e for els in (fur.parts or {}).values() for e in els]
    for suffix, els in (fur.parts or {}).items():
        wj(f"{A}/models/block/{fur.id}_{suffix}.json", model_json(els, tex, render_type=rt))
    wj(f"{A}/models/item/{fur.id}.json", model_json(item_els, tex, display=TALL_DISPLAY if fur.tall or max([e.t[1] for e in item_els] + [0]) > 20 or min([e.f[2] for e in item_els] + [0]) < -4 else None, render_type=rt))
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
    make_animal_textures()
    make_textures3()
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
            "furin": fur.furin, "passable": fur.passable, "tool": fur.tool, "anim": fur.anim, "instrument": fur.instrument,
            "parts": list((fur.parts or {}).keys()),
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
