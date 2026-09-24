"""`date/` 目录持久化。

EXE 相对 HTML 的最大差异：不再依赖浏览器 localStorage / 手动导出，所有数据都
落在 EXE 同目录的 `date/` 文件夹里。

    date/
      configs/<配置名>.json          每个配置一份（可直接与 HTML 导出的 JSON 互换）
      drafts/<配置名>.json           编辑中的崩溃恢复草稿
      library/weapons.json           武器库（等价 localStorage: gs_weaponLib）
      library/artifacts.json         圣遗物库（等价 localStorage: gs_artifactLib）
      history/config_history.json    关闭配置时自动保存的历史
      history/quicktable_history.json 拉表结果历史
      app_settings.json              全局设置（历史保存条数、上次打开的配置……）
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .state import make_config_snapshot, normalize_state, uid

CONFIG_FORMAT = "gidmg-config"
INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def app_dir() -> Path:
    """EXE 所在目录；开发模式下为 exe_src/。"""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def data_dir() -> Path:
    override = os.environ.get("GIDMG_DATA_DIR")
    return Path(override).expanduser().resolve() if override else app_dir() / "date"


def safe_name(name: str) -> str:
    name = INVALID_CHARS.sub("_", (name or "").strip())
    name = name.strip(" .") or "未命名配置"
    return name[:80]


def _read_json(path: Path, default: Any) -> Any:
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def _write_json(path: Path, payload: Any) -> None:
    """原子写：先写临时文件再替换，避免断电/崩溃留下半截文件。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


@dataclass
class ConfigMeta:
    name: str
    path: Path
    saved_at: float = 0.0
    char_names: List[str] = field(default_factory=list)
    total: float = 0.0
    timeline: bool = True
    rotation: float = 20.0
    has_draft: bool = False

    @property
    def saved_text(self) -> str:
        if not self.saved_at:
            return "未知时间"
        return _dt.datetime.fromtimestamp(self.saved_at).strftime("%Y-%m-%d %H:%M")

    @property
    def chars_text(self) -> str:
        return "、".join(self.char_names) if self.char_names else "空配置"


class Storage:
    """date/ 目录的唯一入口。"""

    def __init__(self, root: Optional[Path] = None) -> None:
        self.root = Path(root) if root else data_dir()
        self.configs_dir = self.root / "configs"
        self.drafts_dir = self.root / "drafts"
        self.library_dir = self.root / "library"
        self.history_dir = self.root / "history"

    # -------------------------------------------------- 目录

    def ensure(self) -> None:
        for d in (self.configs_dir, self.drafts_dir, self.library_dir, self.history_dir):
            d.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------- 配置

    def config_path(self, name: str) -> Path:
        return self.configs_dir / f"{safe_name(name)}.json"

    def draft_path(self, name: str) -> Path:
        return self.drafts_dir / f"{safe_name(name)}.json"

    def list_configs(self) -> List[ConfigMeta]:
        self.ensure()
        out: List[ConfigMeta] = []
        for path in sorted(self.configs_dir.glob("*.json")):
            raw = _read_json(path, None)
            if not isinstance(raw, dict):
                continue
            meta = raw.get("meta") if raw.get("format") == CONFIG_FORMAT else None
            state = raw.get("state") if raw.get("format") == CONFIG_FORMAT else raw
            if not isinstance(state, dict):
                continue
            chars = [str(c.get("name", "")) for c in state.get("chars", []) if isinstance(c, dict)]
            out.append(ConfigMeta(
                name=str(raw.get("name") or path.stem),
                path=path,
                saved_at=float((meta or {}).get("savedAt") or path.stat().st_mtime),
                char_names=chars,
                total=float((meta or {}).get("total") or 0.0),
                timeline=bool(state.get("timelineEnabled", True)),
                rotation=float(state.get("rotationDuration") or 20),
                has_draft=self.draft_path(path.stem).exists(),
            ))
        out.sort(key=lambda m: m.saved_at, reverse=True)
        return out

    def config_exists(self, name: str) -> bool:
        return self.config_path(name).exists()

    def unique_name(self, base: str) -> str:
        base = safe_name(base)
        if not self.config_exists(base):
            return base
        i = 2
        while self.config_exists(f"{base} {i}"):
            i += 1
        return f"{base} {i}"

    def load_config(self, name: str) -> Dict[str, Any]:
        raw = _read_json(self.config_path(name), None)
        if raw is None:
            raise FileNotFoundError(f"配置不存在：{name}")
        return normalize_state(raw.get("state") if raw.get("format") == CONFIG_FORMAT else raw)

    def save_config(self, name: str, state: Dict[str, Any], total: float = 0.0) -> Path:
        self.ensure()
        payload = {
            "format": CONFIG_FORMAT,
            "version": "2.1.9",
            "name": safe_name(name),
            "meta": {
                "savedAt": _dt.datetime.now().timestamp(),
                "total": float(total or 0.0),
                "charNames": [c.get("name") for c in state.get("chars", [])],
            },
            "state": json.loads(json.dumps(state, ensure_ascii=False)),
        }
        path = self.config_path(name)
        _write_json(path, payload)
        self.clear_draft(name)
        return path

    def create_config(self, name: str, state: Dict[str, Any]) -> str:
        real = self.unique_name(name)
        self.save_config(real, state)
        return real

    def delete_config(self, name: str) -> None:
        for p in (self.config_path(name), self.draft_path(name)):
            try:
                p.unlink()
            except OSError:
                pass

    def rename_config(self, old: str, new: str) -> str:
        real = self.unique_name(new)
        src, dst = self.config_path(old), self.config_path(real)
        if src.exists():
            raw = _read_json(src, {})
            if isinstance(raw, dict):
                raw["name"] = real
            _write_json(dst, raw)
            try:
                src.unlink()
            except OSError:
                pass
        draft = self.draft_path(old)
        if draft.exists():
            shutil.move(str(draft), str(self.draft_path(real)))
        return real

    def duplicate_config(self, name: str) -> str:
        real = self.unique_name(f"{name} 副本")
        raw = _read_json(self.config_path(name), None)
        if raw is None:
            raise FileNotFoundError(name)
        if isinstance(raw, dict):
            raw["name"] = real
        _write_json(self.config_path(real), raw)
        return real

    def import_config(self, src: Path, name: Optional[str] = None) -> str:
        raw = _read_json(Path(src), None)
        if raw is None:
            raise ValueError("无法解析该 JSON 文件")
        state = raw.get("state") if isinstance(raw, dict) and raw.get("format") == CONFIG_FORMAT else raw
        state = normalize_state(state)
        real = self.unique_name(name or (raw.get("name") if isinstance(raw, dict) else None) or Path(src).stem)
        self.save_config(real, state)
        return real

    def export_config(self, name: str, dst: Path, raw_state: bool = True) -> None:
        """导出成 HTML 版可直接导入的 JSON（raw_state=True 时不带 EXE 外壳）。"""
        state = self.load_config(name)
        _write_json(Path(dst), state if raw_state else {
            "format": CONFIG_FORMAT, "version": "2.1.9", "name": name, "meta": {}, "state": state})

    # -------------------------------------------------- 草稿（崩溃恢复）

    def save_draft(self, name: str, state: Dict[str, Any]) -> None:
        self.ensure()
        _write_json(self.draft_path(name), {
            "savedAt": _dt.datetime.now().timestamp(),
            "state": make_config_snapshot(state) | {"baselines": state.get("baselines", [])},
        })

    def load_draft(self, name: str) -> Optional[Dict[str, Any]]:
        raw = _read_json(self.draft_path(name), None)
        if not isinstance(raw, dict) or not isinstance(raw.get("state"), dict):
            return None
        try:
            return normalize_state(raw["state"])
        except ValueError:
            return None

    def draft_time(self, name: str) -> float:
        raw = _read_json(self.draft_path(name), None)
        return float(raw.get("savedAt", 0.0)) if isinstance(raw, dict) else 0.0

    def clear_draft(self, name: str) -> None:
        try:
            self.draft_path(name).unlink()
        except OSError:
            pass

    # -------------------------------------------------- 武器库 / 圣遗物库

    @property
    def weapons_path(self) -> Path:
        return self.library_dir / "weapons.json"

    @property
    def artifacts_path(self) -> Path:
        return self.library_dir / "artifacts.json"

    def load_weapon_lib(self) -> List[Dict[str, Any]]:
        v = _read_json(self.weapons_path, [])
        return v if isinstance(v, list) else []

    def save_weapon_lib(self, lib: List[Dict[str, Any]]) -> None:
        self.ensure()
        _write_json(self.weapons_path, lib)

    def load_artifact_lib(self) -> List[Dict[str, Any]]:
        v = _read_json(self.artifacts_path, [])
        return v if isinstance(v, list) else []

    def save_artifact_lib(self, lib: List[Dict[str, Any]]) -> None:
        self.ensure()
        _write_json(self.artifacts_path, lib)

    # -------------------------------------------------- 全局设置

    @property
    def settings_path(self) -> Path:
        return self.root / "app_settings.json"

    def load_settings(self) -> Dict[str, Any]:
        v = _read_json(self.settings_path, {})
        base = {"cfgHistCount": 5, "qtHistCount": 10, "lastConfig": None, "windowGeometry": None}
        if isinstance(v, dict):
            base.update(v)
        try:
            base["cfgHistCount"] = int(base["cfgHistCount"])
        except (TypeError, ValueError):
            base["cfgHistCount"] = 5
        try:
            base["qtHistCount"] = int(base["qtHistCount"])
        except (TypeError, ValueError):
            base["qtHistCount"] = 10
        return base

    def save_settings(self, settings: Dict[str, Any]) -> None:
        self.ensure()
        _write_json(self.settings_path, settings)

    def update_settings(self, **kwargs: Any) -> Dict[str, Any]:
        s = self.load_settings()
        s.update(kwargs)
        self.save_settings(s)
        return s

    # -------------------------------------------------- 历史记录

    @property
    def cfg_history_path(self) -> Path:
        return self.history_dir / "config_history.json"

    @property
    def qt_history_path(self) -> Path:
        return self.history_dir / "quicktable_history.json"

    def load_cfg_history(self) -> List[Dict[str, Any]]:
        v = _read_json(self.cfg_history_path, [])
        return v if isinstance(v, list) else []

    def load_qt_history(self) -> List[Dict[str, Any]]:
        v = _read_json(self.qt_history_path, [])
        return v if isinstance(v, list) else []

    @staticmethod
    def _trim(lst: List[Dict[str, Any]], count: int) -> List[Dict[str, Any]]:
        return lst if count < 0 else lst[:max(0, count)]

    def save_cfg_history(self, lst: List[Dict[str, Any]]) -> None:
        self.ensure()
        _write_json(self.cfg_history_path, self._trim(lst, self.load_settings()["cfgHistCount"]))

    def save_qt_history(self, lst: List[Dict[str, Any]]) -> None:
        self.ensure()
        _write_json(self.qt_history_path, self._trim(lst, self.load_settings()["qtHistCount"]))

    def capture_cfg_history(self, state: Dict[str, Any], total: float, config_name: str) -> None:
        """对应 HTML 的 captureCfgHistory()：退出配置时记一笔，内容相同则只刷新时间。"""
        try:
            config = make_config_snapshot(state)
            rec = {
                "id": uid(),
                "time": _dt.datetime.now().timestamp() * 1000,
                "total": float(total or 0.0),
                "charNames": "、".join(str(c.get("name")) for c in state.get("chars", [])),
                "configName": config_name,
                "config": config,
            }
            lst = self.load_cfg_history()
            if lst and json.dumps(lst[0].get("config"), sort_keys=True) == json.dumps(config, sort_keys=True):
                lst[0].update({"time": rec["time"], "total": rec["total"],
                               "charNames": rec["charNames"], "configName": config_name})
            else:
                lst.insert(0, rec)
            self.save_cfg_history(lst)
        except (OSError, TypeError, ValueError):
            pass

    def record_qt_history(self, results: List[Dict[str, Any]], char_info: List[Dict[str, Any]]) -> None:
        try:
            rec = {
                "id": uid(),
                "time": _dt.datetime.now().timestamp() * 1000,
                "count": len(results),
                "bestDps": max((r.get("dps") or 0.0 for r in results), default=0.0),
                "results": results,
                "charInfo": char_info,
            }
            lst = self.load_qt_history()
            lst.insert(0, rec)
            self.save_qt_history(lst)
        except (OSError, TypeError, ValueError):
            pass
