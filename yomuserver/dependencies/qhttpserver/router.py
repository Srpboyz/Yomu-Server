from __future__ import annotations

from typing import Any, Callable, TYPE_CHECKING
import re

from .request import HttpRequest, Method
from .response import HttpResponse
from . import utils


T_Func = Callable[[HttpRequest], HttpResponse]

if TYPE_CHECKING:
    from .handler import RouteHandler


class Route:
    def __init__(self, method: Method, path: str, func: T_Func) -> None:
        has_path_params, path, params = utils.check_regex(path)

        self.path = path
        self.methods = {method: func}
        self.has_path_params = has_path_params
        self._params_converter = params

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Route):
            return False
        return self.path == other.path

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    def matches(self, path: str) -> bool:
        return bool(re.match(self.path, path))

    def get_params(self, path: str) -> dict[str, Any]:
        m = re.search(self.path, path)
        if m is None:
            return {}

        return {
            name: cls(group)
            for group, (name, cls) in zip(m.groups(), self._params_converter.items())
        }


class Router:
    def __init__(self):
        self._paths: list[Route] = []

    def add_route(self, method: Method, path: str, func: T_Func) -> None:
        self._add_route(Route(method, path, func))

    def _add_route(self, route: Route) -> None:
        for other in self._paths:
            if other.path == route.path:
                other.methods.update(**route.methods)
                break
        else:
            self._paths.append(route)

    def add_route_handler(self, handler: RouteHandler) -> None:
        for route in handler.__router__:
            self._add_route(route)

    def get_path_handler(self, path: str) -> Route | None:
        for route in self._paths:
            if route.matches(path):
                return route
