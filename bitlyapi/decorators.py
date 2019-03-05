import asyncio
import logging
from functools import wraps

import aiohttp

logger = logging.getLogger(__name__)


def retry_request(retries: int = 5, timeout: float = 1.0):
    def decorator(func):
        @wraps(func)
        async def request(*args, **kwargs):
            last_exception = None
            retries_count = 0
            while retries_count < retries:
                retries_count += 1
                try:
                    return await func(*args, **kwargs)
                except aiohttp.ClientError as ex:
                    logger.info('Retrying %d because of %s' % (retries_count, ex))
                    last_exception = ex
                    await asyncio.sleep(timeout)
            raise last_exception

        return request

    return decorator
