import asyncio
import logging
import json

import aiohttp
from aiohttp import BasicAuth

from bitlyapi.decorators import retry_request
from bitlyapi.exceptions import ApiStatusException, HttpException,SessionRequiredException, AuthException

logger = logging.getLogger(__name__)

request_retry_count = 5
request_retry_timeout = 1.0


class ResponseObject:
    __slots__ = '_data'

    def __init__(self, data: dict):
        self._data = data

    def __getattr__(self, name):
        if name not in self._data:
            raise AttributeError(f'ResponseObject has no attribute "{name}"')

        return self._data[name]

    def __repr__(self):
        return f'{self.__class__.__name__}({self._data})'


class BitlyAPI:
    ENTRYPOINT = 'https://api-ssl.bitly.com'
    VERSION_PREFIX = 'v3/'
    NON_VERSIONED = {
        'oauth/access_token',
    }
    PATH_METHOD = {
        'oauth/access_token': 'post',
    }
    DEFAULT_METHOD = 'get'

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

    @retry_request(retries=request_retry_count, timeout=request_retry_timeout)
    async def _send_request(self, _method, url, data):
        if self._session is None:
            raise SessionRequiredException()
        return await self._session.request(_method, url, data=data)

    async def _make_request(self, path: str, data):
        is_non_versioned = path in self.NON_VERSIONED
        prefix = '' if is_non_versioned else self.VERSION_PREFIX
        url = f'{self.ENTRYPOINT}/{prefix}{path}'
        method = self.PATH_METHOD.get(path, self.DEFAULT_METHOD)

        if self.token:
            data['access_token'] = self.token

        logger.debug('Request("%s", data=%s)', url, data)
        response = await self._send_request(method, url, data)

        return await self._get_data_from_response(response, is_non_versioned)

    @staticmethod
    async def _get_data_from_response(response, is_non_versioned):
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
        return self._BitlyQuery(self, name)

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

    class _BitlyQuery:
        def __init__(self, api: 'BitlyAPI', path: str):
            self._path = path
            self._api = api

        def __getattr__(self, item):
            return self.__class__(self._api, f'{self._path}/{item}')

        async def __call__(self, **kwargs):

            return await self._api._make_request(path=self._path, data=kwargs)
