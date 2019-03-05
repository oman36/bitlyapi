import asyncio
import logging
import json

import aiohttp
from aiohttp import BasicAuth

from bitlyapi.exceptions import ApiStatusException, HttpException, HttpMethodNotAllowedException,\
    SessionRequiredException, AuthException

logger = logging.getLogger(__name__)


class ResponseObject:
    __slots__ = '_data'

    def __init__(self, data: dict):
        self._data = data

    def __getattr__(self, name):
        if name not in self._data:
            raise AttributeError("ResponseObject has no attribute '{}'".format(name))

        return self._data[name]

    def __repr__(self):
        return '{}({})'.format(self.__class__.__name__, self._data)


class _BitlyQuery:
    PATH_METHOD = {
        'oauth/access_token': 'post',
    }
    DEFAULT_METHOD = 'get'

    def __init__(self, api: 'BitlyAPI', path: str):
        self.path = path
        self.api = api

    def __getattr__(self, item):
        return _BitlyQuery(self.api, '{}/{}'.format(self.path, item))

    async def __call__(self, **kwargs):
        method = self.PATH_METHOD.get(self.path, self.DEFAULT_METHOD)
        return await self.api(_method=method, _path=self.path, **kwargs)


class BitlyAPI:
    ENTRYPOINT = 'https://api-ssl.bitly.com'
    RETRIES = 5
    TIMEOUT = 1
    VERSION_PREFIX = 'v3/'
    NON_VERSIONED = {
        'oauth/access_token',
    }

    def __init__(self, username: str = None, password: str = None,
                 client_id: str = None, client_secret: str = None,
                 token: str = None):
        if not token and not all((username, password, client_id, client_secret)):
            raise AuthException('Token or (username, password, client_id and client_secret) are required')
        self.password = password
        self.username = username
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = token
        self._session = None  # type: aiohttp.ClientSession
        self.lock = asyncio.Lock()

    async def _retry(self, func, *args, **kwargs):
        last_exception = None
        retries_count = 0
        while retries_count < self.RETRIES:
            retries_count += 1
            try:
                return await func(*args, **kwargs)
            except aiohttp.ClientError as ex:
                logger.info('Retrying %d because of %s' % (retries_count, ex))
                last_exception = ex
                await asyncio.sleep(self.TIMEOUT)
        raise last_exception

    async def __call__(self, _method: str, _path: str, **kwargs):
        if self._session is None:
            raise SessionRequiredException()

        if not hasattr(self._session, _method):
            raise HttpMethodNotAllowedException(_method)

        is_non_versioned = _path in self.NON_VERSIONED
        prefix = '' if is_non_versioned else self.VERSION_PREFIX
        url = self.ENTRYPOINT + '/' + prefix + _path
        func = getattr(self._session, _method)
        if self.token:
            kwargs['access_token'] = self.token

        logger.debug('Request("%s", data=%s)', url, kwargs)
        response = await self._retry(func, url, data=kwargs)
        text = await response.text()
        if response.status != 200:
            raise HttpException(response.status, text)

        data = json.loads(text, object_hook=ResponseObject)

        if is_non_versioned:
            status_code = getattr(data, 'status_code', 200)
        else:
            status_code = data.status_code

        if status_code != 200:
            raise ApiStatusException(data.status_code, data.status_txt)

        return data if is_non_versioned else data.data

    def __getattr__(self, name: str):
        return _BitlyQuery(self, name)

    async def _get_token(self) -> str:
        params = {'password': self.password, 'username': self.username, 'grant_type': 'password'}
        response = await self.oauth.access_token(**params)
        return response.access_token

    async def __aenter__(self):
        async with self.lock:
            if self.token:
                self._session = aiohttp.ClientSession()
            else:
                self._session = aiohttp.ClientSession(auth=BasicAuth(self.client_id, self.client_secret))
                try:
                    self.token = await self._get_token()
                except BaseException as e:
                    await self._session.close()
                    self._session = None
                    raise e
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._session.close()
        self._session = None
        return False
