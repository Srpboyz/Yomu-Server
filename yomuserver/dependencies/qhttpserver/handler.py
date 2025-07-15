from typing import Any, Self

from .request import Method
from .router import Route, T_Func

__all__ = ("RouteHandler", "get", "post", "put", "delete")


class RouteHandler:
    __router__: list[Route]
    BASE_PATH: str

    def __new__(cls, *args: Any, **kwargs: Any) -> Self:
        self = super().__new__(cls)

        router: list[Route] = []
        for base in cls.__mro__:
            for name in base.__dict__:
                value = getattr(self, name)

                __route__: tuple[Method, str] | None = getattr(value, "__route__", None)
                if __route__ is None:
                    continue

                method, path = __route__
                route = Route(method, f"{cls.BASE_PATH}{path}", value)
                for r in router:
                    if r.path == route.path:
                        r.methods.update(**route.methods)
                        break
                else:
                    router.append(route)

        self.__router__ = router
        return self


def get(path: str):
    def wrapper(func: T_Func):
        func.__route__ = Method.GET, path
        return func

    return wrapper


def post(path: str):
    def wrapper(func: T_Func):
        func.__route__ = Method.POST, path
        return func

    return wrapper


def put(path: str):
    def wrapper(func: T_Func):
        func.__route__ = Method.PUT, path
        return func

    return wrapper


def delete(path: str):
    def wrapper(func: T_Func):
        func.__route__ = Method.DELETE, path
        return func

    return wrapper
