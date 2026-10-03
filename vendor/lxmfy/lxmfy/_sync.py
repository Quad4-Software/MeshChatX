"""Run callbacks that may be sync or async."""

import asyncio
import inspect


def run_sync(func, *args):
    """Call func and await it when it returns a coroutine."""
    result = func(*args)
    if inspect.iscoroutine(result):
        return asyncio.run(result)
    return result
