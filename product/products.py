import json
from pathlib import Path

BASE = Path(__file__).parent
CATALOG = json.loads((BASE / "catalog.json").read_text())

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "find_suitable_wheelchairs",
        "description": (
            "Search the wheelchair catalog for models that fit a user's weight and needs. "
            "Call once you know at least the user's approximate weight."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "weight_kg": {"type": "number", "description": "User's approximate body weight in kg"},
                "height_cm": {"type": "number", "description": "User's approximate height in cm, if known"},
                "self_propelled": {
                    "type": "boolean",
                    "description": (
                        "true if the user will propel the wheelchair themselves, "
                        "false if a caregiver pushes it"
                    ),
                },
                "needs_tilt": {
                    "type": "boolean",
                    "description": (
                        "true if the user needs tilt-in-space/recline support, e.g. for "
                        "pressure relief or limited trunk control"
                    ),
                },
                "taxi_transport": {
                    "type": "boolean",
                    "description": (
                        "true if the wheelchair needs to be crash-tested for transport "
                        "in a taxi/vehicle while occupied"
                    ),
                },
            },
        },
    },
}


def _depth_fit_score(product: dict, estimated_depth: float) -> float:
    # 0 if the estimate falls inside the seat depth range, else distance to the nearest edge
    lo, hi = product["seat_depth_cm"]
    if lo <= estimated_depth <= hi:
        return 0.0
    return min(abs(estimated_depth - lo), abs(estimated_depth - hi))


def find_suitable_wheelchairs(args: dict) -> dict:
    weight_kg = args.get("weight_kg")
    height_cm = args.get("height_cm")
    self_propelled = args.get("self_propelled")
    needs_tilt = args.get("needs_tilt")
    taxi_transport = args.get("taxi_transport")

    candidates = [product for product in CATALOG if product["category"] == "wheelchair"]
    if weight_kg is not None:
        candidates = [product for product in candidates if weight_kg <= product["max_weight_kg"]]
    if self_propelled is True:
        candidates = [product for product in candidates if product["self_propelled"]]
    if not candidates:
        return {"matches": [], "none_fit": True, "estimate_only": False}

    estimate_only = height_cm is not None

    def sort_key(product: dict) -> float:
        score = 0.0
        if estimate_only:
            score += _depth_fit_score(product, height_cm * 0.24)
        if self_propelled is False and not product["self_propelled"]:
            score -= 10
        if needs_tilt and product["tilt_in_space"]:
            score -= 10
        if taxi_transport and product["taxi_approved"]:
            score -= 10
        return score

    candidates.sort(key=sort_key)
    top = candidates[:3]
    return {
        "matches": [{"name": p["name"], "type": p["type"], "why": p["description"]} for p in top],
        "none_fit": False,
        "estimate_only": estimate_only,
    }
