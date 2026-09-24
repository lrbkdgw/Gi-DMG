"""静态数据表。

本模块是 `Gi DMG v2.1.9.html` 中同名常量表的逐条移植，任何数值改动都必须
同时修改 HTML 与本文件，否则两端结算结果会出现分歧。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

APP_NAME = "Gi DMG"
APP_TITLE = "原神伤害计算器"

# ---------------------------------------------------------------- 元素 / 伤害类型

# id / 中文名 / 主色 / 文字色 / 背景色 / 边框色（对应 HTML 里的 .elem-* 样式）
EL: List[Dict[str, str]] = [
    {"id": "pyro", "n": "火", "color": "#d75a3a", "bg": "#fbe6de", "border": "#f1c5b6"},
    {"id": "hydro", "n": "水", "color": "#2a7fbe", "bg": "#dceefd", "border": "#b9daf5"},
    {"id": "electro", "n": "雷", "color": "#7d55c7", "bg": "#ece2fa", "border": "#d7c3f0"},
    {"id": "cryo", "n": "冰", "color": "#3a9db8", "bg": "#d9f2f6", "border": "#b8e3ea"},
    {"id": "dendro", "n": "草", "color": "#5a9a3a", "bg": "#e3f0d8", "border": "#c6dfb4"},
    {"id": "anemo", "n": "风", "color": "#2b9b7f", "bg": "#d9f2e8", "border": "#b8e3cf"},
    {"id": "geo", "n": "岩", "color": "#b88a2d", "bg": "#f5ebd1", "border": "#e5d2a9"},
    {"id": "physical", "n": "物理", "color": "#6a5f57", "bg": "#ece7e2", "border": "#d7ceca"},
]
EL_IDS: List[str] = [e["id"] for e in EL]
EL_BY_ID: Dict[str, Dict[str, str]] = {e["id"]: e for e in EL}


def element_meta(elem_id: Optional[str]) -> Optional[Dict[str, str]]:
    return EL_BY_ID.get(elem_id or "")


def element_name(elem_id: Optional[str]) -> str:
    meta = element_meta(elem_id)
    return meta["n"] if meta else str(elem_id or "")


DT: List[Dict[str, str]] = [
    {"id": "NA", "n": "普通攻击"},
    {"id": "CA", "n": "重击"},
    {"id": "PA", "n": "下落攻击"},
    {"id": "E", "n": "元素战技"},
    {"id": "Q", "n": "元素爆发"},
    {"id": "other", "n": "其他"},
]

# ---------------------------------------------------------------- 反应表

TRANS_REACTIONS: List[Dict[str, Any]] = [
    {"id": "aggravate", "n": "超激化", "mult": 1.15, "elem": "electro", "quicken": True},
    {"id": "spread", "n": "蔓激化", "mult": 1.25, "elem": "dendro", "quicken": True},
    {"id": "overloaded", "n": "超载", "mult": 2.75, "elem": "pyro"},
    {"id": "superconduct", "n": "超导", "mult": 1.5, "elem": "cryo"},
    {"id": "electrocharged", "n": "感电", "mult": 2.0, "elem": "electro"},
    {"id": "swirl_pyro", "n": "扩散(火)", "mult": 0.6, "elem": "pyro"},
    {"id": "swirl_hydro", "n": "扩散(水)", "mult": 0.6, "elem": "hydro"},
    {"id": "swirl_electro", "n": "扩散(雷)", "mult": 0.6, "elem": "electro"},
    {"id": "swirl_cryo", "n": "扩散(冰)", "mult": 0.6, "elem": "cryo"},
    {"id": "shattered", "n": "碎冰", "mult": 3.0, "elem": "physical"},
    {"id": "bloom", "n": "绽放", "mult": 2.0, "elem": "dendro"},
    {"id": "hyperbloom", "n": "超绽放", "mult": 3.0, "elem": "dendro"},
    {"id": "burgeon", "n": "烈绽放", "mult": 3.0, "elem": "pyro"},
    {"id": "burning", "n": "燃烧", "mult": 0.25, "elem": "pyro"},
]
TRANS_BY_ID: Dict[str, Dict[str, Any]] = {r["id"]: r for r in TRANS_REACTIONS}

SPECIAL_REACTIONS: List[Dict[str, Any]] = [
    {"id": "lunar_charged", "n": "反应月感电", "mult": 1.8, "elem": "electro", "direct": False},
    {"id": "lunar_crystal", "n": "反应月结晶", "mult": 1.6, "elem": "geo", "direct": False},
    {"id": "lunar_bloom_direct", "n": "角色月绽放(直伤)", "mult": 1.0, "elem": "dendro", "direct": True},
    {"id": "lunar_charged_direct", "n": "角色月感电(直伤)", "mult": 3.0, "elem": "electro", "direct": True},
    {"id": "lunar_crystal_direct", "n": "角色月结晶(直伤)", "mult": 1.6, "elem": "geo", "direct": True},
    {"id": "star_sc_direct", "n": "角色星超导(直伤)", "elem": "cryo", "direct": True, "star": True},
    {"id": "star_sd_direct", "n": "角色星扩散(直伤)", "mult": 1.0, "elem": "cryo", "direct": True, "star": True},
    {"id": "star_sd_cryo", "n": "反应星扩散(冰)", "elem": "cryo", "direct": False, "star": True, "cryoChoice": True},
    {"id": "star_sd_anemo", "n": "反应星扩散(风)", "mult": 0.75, "elem": "anemo", "direct": False, "star": True},
]
SPEC_BY_ID: Dict[str, Dict[str, Any]] = {r["id"]: r for r in SPECIAL_REACTIONS}


def get_spec_meta(spec_id: Optional[str]) -> Optional[Dict[str, Any]]:
    return SPEC_BY_ID.get(spec_id or "")


LV_COEFF: Dict[int, float] = {
    1: 17.17, 10: 51.22, 20: 122.15, 25: 155.84, 30: 191.35, 35: 231.93,
    40: 277.37, 45: 328.75, 50: 388.07, 55: 450.28, 60: 530.78, 65: 605.67,
    70: 685.13, 75: 732.55, 80: 1077.44, 85: 1269.76, 90: 1446.85, 95: 1711.20,
    100: 2030.10,
}

# ---------------------------------------------------------------- 天赋效果分类

ECAT: Dict[str, Dict[str, Any]] = {
    "stat": {"n": "面板属性", "opts": [
        {"id": "base_atk", "n": "基础攻击力"}, {"id": "base_def", "n": "基础防御力"},
        {"id": "base_hp", "n": "基础生命值"}, {"id": "atk_flat", "n": "攻击力(固定值)"},
        {"id": "atk_pct", "n": "攻击力 %"}, {"id": "def_flat", "n": "防御力(固定值)"},
        {"id": "def_pct", "n": "防御力 %"}, {"id": "hp_flat", "n": "生命值(固定值)"},
        {"id": "hp_pct", "n": "生命值 %"}, {"id": "em_flat", "n": "元素精通"},
        {"id": "critRate", "n": "暴击率 %"}, {"id": "critDMG", "n": "暴击伤害 %"},
    ]},
    "dmgType": {"n": "伤害类型加成", "opts": [
        {"id": "NA", "n": "普攻伤害 %"}, {"id": "CA", "n": "重击伤害 %"},
        {"id": "PA", "n": "下落攻击伤害 %"}, {"id": "E", "n": "战技伤害 %"},
        {"id": "Q", "n": "爆发伤害 %"}, {"id": "all", "n": "全伤害 %"},
        {"id": "source_dmg_bonus", "n": "目标来源伤害提升 %"},
        {"id": "source_final_mult", "n": "目标来源造成原伤害 %"},
    ]},
    "dmgElem": {"n": "元素伤害加成", "opts": [
        {"id": "elem_" + e["id"], "n": e["n"] + "伤害 %"} for e in EL
    ]},
    "resShred": {"n": "敌人减抗", "opts": [
        {"id": "res_" + e["id"], "n": e["n"] + "抗性 %"} for e in EL
    ]},
    "defense": {"n": "敌人防御", "opts": [
        {"id": "def_shred", "n": "减防 %"}, {"id": "def_ignore", "n": "无视防御 %"},
    ]},
    "reaction": {"n": "反应加成", "opts": [
        {"id": "amp_bonus", "n": "增幅反应加成 %"}, {"id": "trans_aggravate", "n": "超激化加成 %"},
        {"id": "trans_spread", "n": "蔓激化加成 %"}, {"id": "trans_overloaded", "n": "超载加成 %"},
        {"id": "trans_superconduct", "n": "超导加成 %"}, {"id": "trans_electrocharged", "n": "感电加成 %"},
        {"id": "trans_swirl", "n": "扩散加成 %"}, {"id": "trans_shattered", "n": "碎冰加成 %"},
        {"id": "trans_bloom", "n": "绽放加成 %"}, {"id": "trans_hyperbloom", "n": "超绽放加成 %"},
        {"id": "trans_burgeon", "n": "烈绽放加成 %"}, {"id": "trans_burning", "n": "燃烧加成 %"},
    ]},
    "lunar": {"n": "月曜反应", "opts": [
        {"id": "spec_all", "n": "月曜反应伤害 %"}, {"id": "spec_direct", "n": "月曜直伤伤害 %"},
        {"id": "spec_reaction", "n": "月曜反应伤害加成 %"}, {"id": "lunar_charged", "n": "月感电伤害 %"},
        {"id": "lunar_bloom", "n": "月绽放伤害 %"}, {"id": "lunar_crystal", "n": "月结晶伤害 %"},
        {"id": "lunar_base", "n": "月曜反应基础区 %"}, {"id": "lunar_base_charged", "n": "月感电基础区 %"},
        {"id": "lunar_base_bloom", "n": "月绽放基础区 %"}, {"id": "lunar_base_crystal", "n": "月结晶基础区 %"},
        {"id": "spec_ascend", "n": "月曜擢升 %"},
    ]},
    "star": {"n": "星烁反应", "opts": [
        {"id": "star_all", "n": "星烁反应伤害 %"}, {"id": "star_sc_bonus", "n": "星超导增伤 %"},
        {"id": "star_sc_stacks", "n": "星超导叠层层数增加"}, {"id": "star_sd_bonus", "n": "星扩散增伤 %"},
        {"id": "star_base", "n": "星烁反应基础区 %"}, {"id": "star_base_sc", "n": "星超导基础区 %"},
        {"id": "star_base_sd", "n": "星扩散基础区 %"}, {"id": "star_ascend", "n": "星烁擢升 %"},
    ]},
    "feather": {"n": "羽毛效果", "opts": [
        {"id": "atk", "n": "攻击力 %"}, {"id": "def", "n": "防御力 %"}, {"id": "hp", "n": "生命值 %"},
        {"id": "em", "n": "元素精通 %"}, {"id": "fixed", "n": "固定值"},
    ]},
}

BASE_TYPES = [
    "lunar_base", "lunar_base_charged", "lunar_base_bloom", "lunar_base_crystal",
    "star_base", "star_base_sc", "star_base_sd",
]

TRANS_BONUS_NAMES = {
    "aggravate": "超激化", "spread": "蔓激化", "overloaded": "超载", "superconduct": "超导",
    "electrocharged": "感电", "swirl": "扩散", "shattered": "碎冰", "bloom": "绽放",
    "hyperbloom": "超绽放", "burgeon": "烈绽放", "burning": "燃烧",
}

# ---------------------------------------------------------------- 快捷配置助手

QS_ASC_OPTS = [
    {"id": "none", "n": "无"}, {"id": "atk_pct", "n": "攻击力%"}, {"id": "hp_pct", "n": "生命值%"},
    {"id": "def_pct", "n": "防御力%"}, {"id": "em", "n": "元素精通"}, {"id": "cr", "n": "暴击率%"},
    {"id": "cd", "n": "暴击伤害%"}, {"id": "er", "n": "元素充能%"},
] + [{"id": "dmg_" + e["id"], "n": e["n"] + "伤害加成%"} for e in EL]

QS_WEAPON_SUB_OPTS = [
    {"id": "none", "n": "无"}, {"id": "atk_pct", "n": "攻击力%"}, {"id": "hp_pct", "n": "生命值%"},
    {"id": "def_pct", "n": "防御力%"}, {"id": "em", "n": "元素精通"}, {"id": "cr", "n": "暴击率%"},
    {"id": "cd", "n": "暴击伤害%"}, {"id": "er", "n": "元素充能%"}, {"id": "dmg_physical", "n": "物理伤害%"},
]

QS_SAND_OPTS = [
    {"id": "none", "n": "无"}, {"id": "atk_pct", "n": "攻击%"}, {"id": "hp_pct", "n": "生命%"},
    {"id": "def_pct", "n": "防御%"}, {"id": "em", "n": "精通"},
]

QS_GOBLET_OPTS = [
    {"id": "none", "n": "无"}, {"id": "atk_pct", "n": "攻击%"}, {"id": "hp_pct", "n": "生命%"},
    {"id": "def_pct", "n": "防御%"}, {"id": "em", "n": "精通"},
] + [{"id": "dmg_" + e["id"], "n": e["n"] + "伤害%"} for e in EL]

QS_CIRCLET_OPTS = [
    {"id": "none", "n": "无"}, {"id": "atk_pct", "n": "攻击%"}, {"id": "hp_pct", "n": "生命%"},
    {"id": "def_pct", "n": "防御%"}, {"id": "em", "n": "精通"}, {"id": "cr", "n": "暴击率"},
    {"id": "cd", "n": "暴击伤害"},
]

WPN_DATA: Dict[int, Dict[int, Dict[str, Any]]] = {
    5: {
        542: {"atk1": 44, "sub": {"hp_pct": 66.2, "atk_pct": 66.2, "def_pct": 82.7, "dmg_physical": 82.7, "er": 73.5, "em": 265, "cr": 44.1, "cd": 88.2}},
        608: {"atk1": 46, "sub": {"hp_pct": 49.6, "atk_pct": 49.6, "def_pct": 62.0, "dmg_physical": 62.0, "er": 55.1, "em": 198, "cr": 33.1, "cd": 66.2}},
        674: {"atk1": 48, "sub": {"hp_pct": 33.1, "atk_pct": 33.1, "def_pct": 41.3, "dmg_physical": 41.3, "er": 36.8, "em": 132, "cr": 22.1, "cd": 44.1}},
        741: {"atk1": 49, "sub": {"hp_pct": 16.5, "atk_pct": 16.5, "def_pct": 20.7, "dmg_physical": 20.7, "er": 18.4, "em": 66, "cr": 11.0, "cd": 22.1}},
    },
    4: {
        454: {"atk1": 41, "sub": {"hp_pct": 55.1, "atk_pct": 55.1, "def_pct": 69.0, "dmg_physical": 69.0, "er": 61.3, "em": 221, "cr": 36.8, "cd": 73.5}},
        510: {"atk1": 42, "sub": {"hp_pct": 41.3, "atk_pct": 41.3, "def_pct": 51.7, "dmg_physical": 51.7, "er": 45.9, "em": 165, "cr": 27.6, "cd": 55.1}},
        565: {"atk1": 44, "sub": {"hp_pct": 27.6, "atk_pct": 27.6, "def_pct": 34.5, "dmg_physical": 34.5, "er": 30.6, "em": 110, "cr": 18.4, "cd": 36.8}},
        620: {"atk1": 45, "sub": {"hp_pct": 13.8, "atk_pct": 13.8, "def_pct": 17.2, "dmg_physical": 17.2, "er": 15.3, "em": 55, "cr": 9.2, "cd": 18.4}},
    },
    3: {
        354: {"atk1": 38, "sub": {"hp_pct": 46.9, "atk_pct": 46.9, "def_pct": 58.6, "dmg_physical": 58.6, "er": 52.1, "em": 187, "cr": 31.2, "cd": 62.4}},
        401: {"atk1": 39, "sub": {"hp_pct": 35.2, "atk_pct": 35.2, "def_pct": 44.0, "dmg_physical": 44.0, "er": 39.0, "em": 141, "cr": 23.4, "cd": 46.9}},
        448: {"atk1": 40, "sub": {"hp_pct": 23.5, "atk_pct": 23.5, "def_pct": 29.3, "dmg_physical": 29.3, "er": 26.1, "em": 94, "cr": 15.6, "cd": 31.2}},
    },
}

WPN_ATK_FRAC = {1: 0.0, 20: 0.155, 40: 0.385, 50: 0.50, 60: 0.62, 70: 0.745, 80: 0.87, 90: 1.0}
WPN_SUB_FRAC = {1: 0.218, 20: 0.387, 40: 0.563, 50: 0.651, 60: 0.739, 70: 0.826, 80: 0.913, 90: 1.0}

ASC_MAX = {
    "none": 0, "atk_pct": 28.8, "hp_pct": 28.8, "def_pct": 36.0, "em": 115.2, "cr": 19.2,
    "cd": 38.4, "er": 32.0, "dmg_pyro": 28.8, "dmg_hydro": 28.8, "dmg_electro": 28.8,
    "dmg_cryo": 28.8, "dmg_dendro": 28.8, "dmg_anemo": 28.8, "dmg_geo": 28.8, "dmg_physical": 36.0,
}
ASC_MULT = [0, 1, 1, 2, 2, 3, 4]

# 圣遗物副词条单条均值 / 主词条满级数值
ART_SUB_VALUE = {
    "atk_pct": 4.96, "hp_pct": 4.96, "def_pct": 6.2, "em": 19.82, "cr": 3.31, "cd": 6.62,
    "atk_flat": 16.54, "hp_flat": 253.94, "def_flat": 19.68,
}
ART_MAIN_VALUE = {
    "atk_pct": 46.6, "hp_pct": 46.6, "def_pct": 58.3, "em": 186.5, "cr": 31.1, "cd": 62.2,
    "dmg": 46.6, "physical_dmg": 58.3,
}
QS_MAIN_NAMES = {
    "atk_pct": "攻击力+46.6%", "hp_pct": "生命值+46.6%", "def_pct": "防御力+58.3%",
    "em": "元素精通+186.5", "cr": "暴击率+31.1%", "cd": "暴击伤害+62.2%",
}
QS_SUB_NAMES = {
    "atk_pct": "攻击力%", "hp_pct": "生命值%", "def_pct": "防御力%", "em": "精通",
    "cr": "暴击率", "cd": "暴击伤害", "atk_flat": "小攻击", "hp_flat": "小生命", "def_flat": "小防御",
}

# ---------------------------------------------------------------- 公式速览页

FORMULA_REACTS = [
    {"n": "超载", "m": 2.75}, {"n": "感电", "m": 2.0}, {"n": "超导", "m": 1.5},
    {"n": "碎冰", "m": 3.0}, {"n": "绽放", "m": 2.0}, {"n": "超绽放", "m": 3.0},
    {"n": "烈绽放", "m": 3.0}, {"n": "扩散", "m": 0.6}, {"n": "燃烧", "m": 0.25},
    {"n": "超激化", "m": 1.15}, {"n": "蔓激化", "m": 1.25}, {"n": "月感电", "m": 1.8},
    {"n": "月结晶", "m": 1.6}, {"n": "月绽放", "m": 1.0}, {"n": "星扩散(风)", "m": 0.75},
    {"n": "星扩散(冰)", "m": 2}, {"n": "星扩散(冰·高)", "m": 3},
]

# 公式总览（HTML 用 KaTeX 渲染 LaTeX，EXE 直接使用等价的纯文本公式排版）
FORMULA_SECTIONS: List[Dict[str, Any]] = [
    {
        "title": "普通伤害",
        "formulas": [
            "基础伤害 = 计入属性 × 倍率%",
            "最终伤害 = 基础伤害 × 伤害加成区 × 暴击区 × 防御区 × 抗性区 × 增幅区 × 独立乘区",
        ],
        "notes": ["计入属性可选「固定值」，此时 基础伤害 = 固定值 × 倍率%。"],
    },
    {
        "title": "增幅反应（蒸发 / 融化）",
        "formulas": ["增幅区 = 基础倍率 × ( 1 + 2.78 × 精通/(精通+1400) + 增幅反应加成% )"],
        "notes": [],
    },
    {
        "title": "剧变反应（不可暴击，不吃防御区与伤害加成）",
        "formulas": ["伤害 = 等级系数 × 反应倍率 × ( 1 + 16 × 精通/(精通+2000) + 剧变加成% ) × 抗性区"],
        "notes": ["「段数」为该来源在单轮循环内的触发次数，来源总伤 = 单次伤害 × 段数。"],
    },
    {
        "title": "特殊直伤（月曜 / 星超导 / 星扩散）",
        "formulas": [
            "伤害 = 计入属性 × 倍率% × 反应系数 × 基础区 × ( 1 + 6 × 精通/(精通+2000) + 直伤加成% )",
            "           × 暴击区 × 抗性区 × 擢升 × 独立乘区",
            "基础区 = 1 + 对应反应基础区%",
        ],
        "notes": [
            "月曜反应基础区 / 月感电、月绽放、月结晶基础区；星烁反应基础区 / 星超导、星扩散基础区，"
            "天赋默认作用于全队。该来源的全部伤害（含羽毛附加伤害）均乘基础区。",
        ],
    },
    {
        "title": "特殊反应多角色贡献",
        "formulas": [
            "月曜(月感电/月结晶):  w = ( 1, 1/2, 1/12, 1/12 )",
            "星扩散(风):  w = ( 3/5, 3/10, 1/20, 1/20 )",
            "星扩散(冰):  w = ( 3/5, 3/10, 1/20, 1/20 )",
            "伤害 = Σ 组分ᵢ × wᵢ   ( i = 1..4 )",
            "组分 = 等级系数 × 反应倍率 × 基础区 × ( 1 + 6 × 精通/(精通+2000) + 反应伤害加成% )",
            "           × 暴击区 × 抗性区 × 擢升 × 独立乘区",
        ],
        "notes": [
            "月感电 / 月结晶：各参与角色分别计算组分，按伤害从高到低加权求和；仅有 1 名参与角色时自然取 ×1。",
            "星扩散(风)：风元素参与角色中伤害最高 ×3/5（无风元素参与时该槽位为空），其余参与角色按伤害从高到低 ×3/10、×1/20、×1/20。",
            "星扩散(冰)：挂冰角色中伤害最高 ×3/5、挂风角色中伤害最高 ×3/10（无对应元素参与时该槽位为空），其余按 ×1/20、×1/20。",
        ],
    },
    {
        "title": "星超导 / 星扩散",
        "formulas": [
            "星超导系数(n) = 1.00            (n = 0)",
            "星超导系数(n) = 1.45 + 0.05×(n-1)   (n ≥ 1)",
            "星扩散直伤系数 = 1，  反应星扩散(冰) = 2/3，  反应星扩散(风) = 0.75",
        ],
        "notes": [
            "星超导仅直伤，天赋可超过 12 层。角色星超导 / 角色星扩散直伤的伤害元素跟随伤害归属角色的元素"
            "（雷元素角色造成雷伤、风元素角色造成风伤）。",
        ],
    },
    {
        "title": "羽毛效果",
        "formulas": ["附加伤害 = 天赋所属角色面板属性 × 数值%   或   固定值"],
        "notes": [
            "面板按天赋所属角色结算，而非羽毛目标伤害来源的计入角色。普通直伤并入基础伤害区；"
            "剧变吃精通×抗性；星/月反应吃基础区 × 抗性 × 暴击 × 曜升。",
        ],
    },
    {
        "title": "等级系数",
        "formulas": ["等级系数(lv) = c_lo + (c_hi - c_lo) × (lv - lv_lo) / (lv_hi - lv_lo)"],
        "notes": [],
    },
]

# 伤害占比饼图配色
ELEM_COLOR_MAP = {
    "pyro": "#d75a3a", "hydro": "#2a7fbe", "electro": "#7d55c7", "cryo": "#3a9db8",
    "dendro": "#5a9a3a", "anemo": "#2b9b7f", "geo": "#b88a2d", "physical": "#6a5f57",
    "reaction": "#e67e22",
}
EXTRA_PALETTE = [
    "#e05638", "#258cdb", "#7c4dff", "#00acc1", "#43a047",
    "#00897b", "#d88d22", "#78909c", "#d81b60", "#8e24aa",
]
