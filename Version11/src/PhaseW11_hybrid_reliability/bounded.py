"""Bounded wait helper. Linux uses SIGALRM; Windows uses a worker thread."""
from __future__ import annotations

import os
import signal
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeout
from typing import Callable, TypeVar

T = TypeVar("T")


class TimeoutExpired(TimeoutError):
    """Call exceeded the Hybrid reliability budget."""


def run_with_timeout(fn: Callable[[], T], timeout_s: float) -> T:
    """
    Run fn and raise TimeoutExpired if it exceeds timeout_s.

    timeout_s <= 0 disables the bound (caller waits until fn returns).
    """
    if timeout_s is None or float(timeout_s) <= 0:
        return fn()
    budget = float(timeout_s)
    if os.name == "nt" or not hasattr(signal, "SIGALRM") or not hasattr(signal, "setitimer"):
        return _thread_timeout(fn, budget)
    return _alarm_timeout(fn, budget)


def _thread_timeout(fn: Callable[[], T], timeout_s: float) -> T:
    executor = ThreadPoolExecutor(max_workers=1)
    try:
        future = executor.submit(fn)
        try:
            return future.result(timeout=timeout_s)
        except FuturesTimeout as exc:
            future.cancel()
            raise TimeoutExpired(f"exceeded {timeout_s}s") from exc
    finally:
        try:
            executor.shutdown(wait=False, cancel_futures=True)
        except TypeError:
            executor.shutdown(wait=False)


def _alarm_timeout(fn: Callable[[], T], timeout_s: float) -> T:
    def _handler(_signum, _frame):
        raise TimeoutExpired(f"exceeded {timeout_s}s")

    previous = signal.signal(signal.SIGALRM, _handler)
    try:
        signal.setitimer(signal.ITIMER_REAL, timeout_s)
        try:
            return fn()
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0.0)
    finally:
        signal.signal(signal.SIGALRM, previous)
