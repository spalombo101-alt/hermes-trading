class SchemaError(RuntimeError):
    """Raised when an adapter returns an unexpected schema."""

REQUIRED_VERSION = "1.0"

def require_schema(payload: dict) -> dict:
    if payload.get("schema_version") != REQUIRED_VERSION:
        raise SchemaError(f"adapter schema mismatch: {payload!r}")
    return payload
