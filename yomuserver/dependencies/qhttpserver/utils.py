from logging import Logger
from functools import wraps
from typing import Callable
import re

MATCH = re.compile(r"<([a-zA-Z_]+):?([a-zA-Z]+)?>")
TYPES = {"int": (r"(\d+)", int), "float": (r"(\d+\.\d+)", float)}


def check_regex(path: str) -> tuple[bool, str, dict]:
    params = {}
    new_path = path

    offset = 0
    for m in MATCH.finditer(path):
        name, group_type = m.groups()
        pattern, cls = TYPES.get(group_type, (r"([\w_.-]+)", str))
        params[name] = cls

        start, end = m.start(), m.end()
        new_path = new_path[: start + offset] + pattern + new_path[end + offset :]

        offset += len(pattern) - len(path[start:end])

    new_path += r"?" if new_path.endswith("/") else "/?"
    new_path = f"^{new_path}$"

    return bool(params), new_path, params


def pyqtSlot(logger: Logger | None = None):
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                func(*args, **kwargs)
            except Exception as e:
                if logger is not None:
                    logger.exception(
                        f"An exception occured while running {func.__name__}",
                        exc_info=e,
                    )

        return wrapper

    return decorator
