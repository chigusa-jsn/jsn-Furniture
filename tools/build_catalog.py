"""家具カタログ（HTML 1枚）を作る：python3 tools/build_catalog.py <絵のフォルダ> <出力.html>"""
import base64, io, json, os, sys
from PIL import Image

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
IMG, OUT = sys.argv[1], sys.argv[2]
specs = json.load(open(f"{ROOT}/src/main/resources/jsn_furniture_specs.json", encoding="utf-8"))
ja = json.load(open(f"{ROOT}/src/main/resources/assets/jsn_furniture/lang/ja_jp.json", encoding="utf-8"))
WOODS = ["oak", "spruce", "birch", "jungle", "acacia", "dark_oak", "mangrove", "cherry", "bamboo", "crimson", "warped"]
WOOD_JA = ["オーク", "トウヒ", "シラカバ", "ジャングル", "アカシア", "ダークオーク", "マングローブ", "サクラ", "竹", "真紅", "歪み"]
WOOD_RGB = ["#b8945f", "#7a5a35", "#d7c185", "#b88764", "#ad5d32", "#4f3218", "#773934", "#e3b4ad", "#d1bd5b", "#6b344b", "#2b6963"]
COLORS = ["white", "orange", "magenta", "light_blue", "yellow", "lime", "pink", "gray", "light_gray", "cyan", "purple", "blue", "brown", "green", "red", "black"]
COLOR_JA = ["白", "橙", "赤紫", "空色", "黄色", "黄緑", "桃色", "灰色", "薄灰色", "青緑", "紫", "青", "茶色", "緑", "赤", "黒"]
COLOR_RGB = ["#f0f0f0", "#f07613", "#bd44b3", "#3aafd9", "#f8c527", "#70b919", "#ed8dac", "#3e4447", "#8e8e86", "#158991", "#792aac", "#35399d", "#724728", "#546d1b", "#a12722", "#141519"]

imgs = {}
for f in sorted(os.listdir(IMG)):
    buf = io.BytesIO()
    Image.open(f"{IMG}/{f}").save(buf, "WEBP", lossless=True)
    imgs[f[:-4]] = "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()

kind_of = {s["id"]: s for s in specs["furniture"]}
DO = {"pet": "ペットが座る", "seat": "座れる", "storage": "しまえる", "lamp": "つく・消える", "curtain": "開け閉め", "display": "飾れる", "furin": "音が鳴る",
      "shishi": "音が鳴る", "sink": "水をくめる"}


def tags(i):
    s = kind_of.get(i)
    out = []
    if s:
        if s["kind"] in DO:
            out.append(DO[s["kind"]])
        if s["kind"] == "storage":
            out[-1] += f"（{s['rows'] * 9}マス）"
        if s["tall"]:
            out.append("2マスの高さ")
        if s["passable"]:
            out.append("通り抜けられる")
    elif i.endswith("bed") or i == "futon":
        out.append("寝られる")
    elif i in ("shoji", "fusuma"):
        out.append("開け閉め")
    return out


groups = []
# 木の家具
wood_types = []
for suffix in ["chair", "stool", "bench", "table", "coffee_table", "desk", "shelf", "cabinet", "wardrobe", "counter", "chabudai", "bed"]:
    ids = [f"{w}_{suffix}" for w in WOODS]
    name = ja[f"block.jsn_furniture.oak_{suffix}"].replace("オークの", "")
    wood_types.append({"name": name, "ids": ids, "tags": tags(ids[0])})
color_types = []
for suffix in ["sofa", "curtain", "zabuton", "noren", "pet_bed", "paw_rug"]:
    ids = [f"{c}_{suffix}" for c in COLORS]
    name = ja[f"block.jsn_furniture.red_{suffix}"].replace("赤の", "")
    color_types.append({"name": name, "ids": ids, "tags": tags(ids[0])})
west, wa, furin, animal = [], [], [], []
for s in specs["furniture"]:
    i = s["id"]
    if any(i.endswith("_" + x) for x in ["chair", "stool", "bench", "table", "coffee_table", "desk", "shelf", "cabinet", "wardrobe", "counter", "chabudai",
                                         "sofa", "curtain", "zabuton", "noren", "pet_bed", "paw_rug"]):
        continue
    item = {"id": i, "name": ja[f"block.jsn_furniture.{i}"], "tags": tags(i)}
    is_animal = i.startswith(("plush_", "maneki", "kitsune", "tanuki_", "daruma", "cat_tower", "dog_house", "food_bowl", "water_bowl", "neko_", "kuma_"))
    (furin if i.startswith("furin") else animal if is_animal else wa if s["tab"] == "wa" else west).append(item)
for i in ["futon", "shoji", "fusuma"]:
    wa.append({"id": i, "name": ja[f"block.jsn_furniture.{i}"], "tags": tags(i)})
SOUND = {**{f"furin_{a}": "高く澄んだ音" for a in ["cat_white"]}, "furin_nanbu": "低く長く響く", "furin_brass": "やわらかく響く", "furin_ceramic": "短くやさしい", "furin_bamboo": "カラコロ"}
for f in furin:
    f["tags"] = [SOUND.get(f["id"], "高く澄んだ音")]

data = {"img": imgs, "wood": wood_types, "color": color_types, "west": west, "wa": wa, "furin": furin, "animal": animal,
        "woods": [[a, b] for a, b in zip(WOOD_JA, WOOD_RGB)], "colors": [[a, b] for a, b in zip(COLOR_JA, COLOR_RGB)]}
total = len(specs["furniture"]) + len(specs["beds"]) + len(specs["doors"])
html = open(f"{ROOT}/tools/catalog_template.html", encoding="utf-8").read()
html = html.replace("__TOTAL__", str(total)).replace("__DATA__", json.dumps(data, ensure_ascii=False))
open(OUT, "w", encoding="utf-8").write(html)
print(OUT, len(html) // 1024, "KB")
