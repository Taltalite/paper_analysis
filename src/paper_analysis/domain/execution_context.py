"""任务局部上下文；只承载协议，不引用供应商或具体 pipeline。"""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
import inspect
from typing import Any, Iterator

_current: ContextVar[Any] = ContextVar("paper_execution", default=None)


def current_execution() -> Any:
    return _current.get()


@contextmanager
def execution_scope(ledger: Any) -> Iterator[Any]:
    token = _current.set(ledger)
    try:
        yield ledger
    finally:
        _current.reset(token)


def scoped_execution(function: Any) -> Any:
    """作用域在调用方建立；async gather 继承，子进程由 service 重新绑定。"""
    if inspect.iscoroutinefunction(function):
        @wraps(function)
        async def async_call(*args: Any, **kwargs: Any) -> Any:
            with execution_scope(kwargs.get("execution_context") or current_execution()):
                return await function(*args, **kwargs)
        return async_call
    @wraps(function)
    def call(*args: Any, **kwargs: Any) -> Any:
        with execution_scope(kwargs.get("execution_context") or current_execution()):
            return function(*args, **kwargs)
    return call


def agent_limits() -> dict[str, Any]:
    ledger = current_execution()
    intensity = ledger.policy.intensity.value if ledger else "standard"
    return {"max_iter": {"light": 3, "standard": 6, "deep": 10}[intensity], "max_retry_limit": 0}
