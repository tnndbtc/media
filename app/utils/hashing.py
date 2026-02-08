"""Cache key generation utilities."""

import hashlib
import json
from typing import Any


def generate_cache_key(prefix: str, *args: Any, **kwargs: Any) -> str:
    """Generate a deterministic cache key from arguments.

    Args:
        prefix: Key prefix (e.g., 'search', 'query')
        *args: Positional arguments to include in key
        **kwargs: Keyword arguments to include in key

    Returns:
        Deterministic cache key string
    """
    # Create a hashable representation
    key_data = {
        "args": [_serialize_value(arg) for arg in args],
        "kwargs": {k: _serialize_value(v) for k, v in sorted(kwargs.items())},
    }

    # Create deterministic JSON string
    json_str = json.dumps(key_data, sort_keys=True, default=str)

    # Hash the JSON string
    hash_value = hashlib.sha256(json_str.encode()).hexdigest()[:16]

    return f"{prefix}:{hash_value}"


def _serialize_value(value: Any) -> Any:
    """Serialize a value for cache key generation."""
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    elif isinstance(value, (list, tuple)):
        return [_serialize_value(v) for v in value]
    elif isinstance(value, dict):
        return {k: _serialize_value(v) for k, v in sorted(value.items())}
    elif hasattr(value, "model_dump"):
        # Pydantic model
        return value.model_dump()
    else:
        return str(value)


def generate_media_id(source: str, original_id: str | int) -> str:
    """Generate a unified media ID.

    Args:
        source: Media source (e.g., 'pexels', 'pixabay')
        original_id: Original ID from the source

    Returns:
        Unified media ID string
    """
    return f"{source}_{original_id}"
