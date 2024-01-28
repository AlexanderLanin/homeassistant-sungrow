import sys
from contextlib import asynccontextmanager, contextmanager


@asynccontextmanager
async def async_keep_valid_unless_exception(obj):
    try:
        await obj.__aenter__()
        yield obj
    except Exception:
        await obj.__aexit__(*sys.exc_info())


@contextmanager
def sync_keep_valid_unless_exception(obj):
    try:
        obj.__aenter__()
        yield obj
    except Exception:
        obj.__aexit__(*sys.exc_info())
        raise


@contextmanager
def replace_exception(to_be_replaced, replace_with, replace_with_args):
    try:
        yield
    except to_be_replaced:
        raise replace_with(*replace_with_args) from None
