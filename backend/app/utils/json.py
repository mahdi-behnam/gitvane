import json
from typing import Any


def safe_json_dumps(data: Any) -> str:
    """Safely serializes data to json string"""
    return json.dumps(data, default=str)
