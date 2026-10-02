from uuid import UUID, uuid5


WP3_ID_NAMESPACE = UUID("a2b720c7-5bcd-4d43-ae5f-e649b012e7a4")


def canonical_id(value: str) -> str:
    """Keep UUID keys; map legacy text keys to stable UUIDs."""
    try:
        return str(UUID(value))
    except ValueError:
        return str(uuid5(WP3_ID_NAMESPACE, value))
