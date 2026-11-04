def escape_like(value: str) -> str:
    """Escape LIKE/ILIKE wildcards so user input is matched literally (use with escape='\\\\')."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
