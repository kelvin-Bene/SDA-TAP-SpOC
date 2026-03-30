import os


def is_demo_mode() -> bool:
    return os.getenv("DEMO_MODE", "").lower() in ("true", "1", "yes")
