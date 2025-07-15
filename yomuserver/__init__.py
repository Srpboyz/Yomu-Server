from .core import YomuServerExtension


def setup(*args, **kwargs) -> YomuServerExtension:
    return YomuServerExtension(*args, **kwargs)
