from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import yaml


@dataclass(frozen=True)
class ParserPolicy:
    name: str
    residual_tolerance: float
    tx_rules: List[str]


_POLICY_CACHE: Dict[str, Dict] = {}


def _default_policy_path() -> Path:
    """
    policy.yaml lives at repository root (one level above api/).
    """
    return Path(__file__).resolve().parents[3] / "policy.yaml"


def load_policy(path: str | Path | None = None) -> Dict:
    """
    Load and cache the YAML policy definition.
    """
    target = Path(path) if path else _default_policy_path()
    cache_key = str(target)
    if cache_key in _POLICY_CACHE:
        return _POLICY_CACHE[cache_key]

    if not target.exists():
        _POLICY_CACHE[cache_key] = {}
        return {}

    with target.open("r", encoding="utf-8") as fp:
        data = yaml.safe_load(fp) or {}
    _POLICY_CACHE[cache_key] = data
    return data


def pick_bank_profile(page1_text: str, policy: Dict) -> ParserPolicy:
    defaults = policy.get("defaults") or {}
    residual_tol = float(defaults.get("residual_tolerance", 1.0))
    default_rules = list(defaults.get("tx_rules", []))

    profiles = policy.get("profiles") or {}
    best_name: Optional[str] = None
    best_hits = 0
    for name, cfg in profiles.items():
        hits = 0
        for pattern in cfg.get("detect", []):
            try:
                if re.search(pattern, page1_text or "", re.IGNORECASE):
                    hits += 1
            except re.error:
                continue
        if hits > best_hits:
            best_name = name
            best_hits = hits

    if best_name:
        cfg = profiles.get(best_name, {})
        return ParserPolicy(
            name=best_name,
            residual_tolerance=float(cfg.get("residual_tolerance", residual_tol)),
            tx_rules=list(cfg.get("tx_rules", default_rules)) or default_rules,
        )

    return ParserPolicy(
        name="generic",
        residual_tolerance=residual_tol,
        tx_rules=default_rules,
    )

