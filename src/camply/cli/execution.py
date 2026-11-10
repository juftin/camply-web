"""Run foreground provider operations with safe diagnostics and signal cleanup."""

import asyncio
import contextlib
import signal
from collections.abc import Awaitable, Callable, Iterator, MutableMapping
from typing import Any, NoReturn, TypeVar

import click
import structlog
from pydantic import ValidationError

_T = TypeVar("_T")


def _discard_provider_log(
    _: object, __: str, ___: MutableMapping[str, Any]
) -> NoReturn:
    """Keep provider response payloads and exception credentials out of terminal logs."""
    raise structlog.DropEvent


@contextlib.contextmanager
def _quiet_provider_logs() -> Iterator[None]:
    """Scope provider logging suppression to this foreground command only.

    Public diagnostics are emitted explicitly without HTTP headers, settings or
    exception payloads. Restoring configuration preserves serving behavior.
    """
    previous = structlog.get_config()
    structlog.configure(
        processors=[_discard_provider_log], cache_logger_on_first_use=False
    )
    try:
        yield
    finally:
        structlog.configure(**previous)


async def _cancellable(operation: Callable[[], Awaitable[_T]]) -> _T:
    """Translate termination into cancellation so owned-resource finally blocks run."""
    loop = asyncio.get_running_loop()
    task = asyncio.current_task()
    installed = False
    previous = signal.getsignal(signal.SIGTERM)
    if task is not None:
        try:
            loop.add_signal_handler(signal.SIGTERM, task.cancel)
            installed = True
        except (NotImplementedError, RuntimeError, ValueError):
            pass  # Windows and non-main-thread invocations have no loop signal API.
    try:
        return await operation()
    finally:
        if installed:
            loop.remove_signal_handler(signal.SIGTERM)
            signal.signal(signal.SIGTERM, previous)


def run(operation: Callable[[], Awaitable[_T]]) -> _T:
    """Run async commands with sanitized failures and deterministic client cleanup."""
    try:
        with _quiet_provider_logs():
            return asyncio.run(_cancellable(operation))
    except (KeyboardInterrupt, asyncio.CancelledError) as exc:
        raise click.Abort() from exc
    except ValidationError as exc:
        raise click.ClickException(
            "Provider returned invalid data (ValidationError); try again later."
        ) from exc
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    except Exception as exc:
        raise click.ClickException(
            f"Provider request failed ({type(exc).__name__}); check connectivity and try again."
        ) from exc
