import json
from pathlib import Path


_CONFIG_PATH = Path(__file__).resolve().parents[1] / "data" / "observatory_config.json"

with _CONFIG_PATH.open(encoding="utf-8") as _config_file:
    OBSERVATORY_CONFIG = json.load(_config_file)


def skills_gap_status(demand: int, supply: int) -> str:
    threshold = OBSERVATORY_CONFIG["skills_gap"]
    if demand and supply == 0:
        return "shortage"
    if demand and demand / supply >= threshold["shortage_ratio"]:
        return "shortage"
    if supply and demand == 0:
        return "surplus"
    if supply and demand and supply / demand >= threshold["surplus_ratio"]:
        return "surplus"
    return "balanced"
