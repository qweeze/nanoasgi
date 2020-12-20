import json
import re
from collections import defaultdict
from collections.abc import Mapping
from functools import partial
from typing import List, NamedTuple, Tuple, Union
from urllib.parse import parse_qsl


class MultiDict(Mapping):
    def __init__(self, items):
        self._data = defaultdict(list)
        self._len = 0
        for k, v in items:
            self._data[self._transform_key(k.decode())].append(v.decode())
            self._len += 1

    @staticmethod
    def _transform_key(key):
        return key

    def get_list(self, key):
        return self._data[self._transform_key(key)]

    def __getitem__(self, key):
        try:
            return self.get_list(key)[0]
        except IndexError:
            raise KeyError(key)

    def __iter__(self):
        return (k for k in self._data for _ in self._data[k])

    def __len__(self):
        return self._len

    def __repr__(self):
        return f'<{self.__class__.__name__}: {self._data!r}>'


class CaselessMultiDict(MultiDict):
    @staticmethod
    def _transform_key(key):
        return key.lower()


class Request(NamedTuple):
    path: str
    method: str
    headers: CaselessMultiDict
    query: MultiDict
    body: bytes

    @property
    def text(self) -> str:
        return self.body.decode()

    @property
    def json(self) -> object:
        return json.loads(self.body)


class Response(NamedTuple):
    data: Union[bytes, str, list, dict, None] = None
    status: int = 200
    headers: List[Tuple[str, str]] = []

    @property
    def body(self) -> bytes:
        if self.data is None:
            return b''
        elif isinstance(self.data, bytes):
            return self.data
        elif isinstance(self.data, str):
            return self.data.encode()
        elif isinstance(self.data, (dict, list)):
            return json.dumps(self.data).encode()
        else:
            raise TypeError(type(self.data))


class App:
    def __init__(self):
        self._routes = []
        self._listeners = {}

    def route(self, method, path):
        return partial(self._add_route, path, method)

    def on(self, event):
        return partial(self._add_event_listener, event)

    def _add_route(self, path, method, handler):
        param_re = r'{([a-zA-Z_][a-zA-Z0-9_]*)}'
        path_re = re.sub(param_re, r'(?P<\1>\\w+)', path)
        self._routes.append((re.compile(path_re), method, handler))
        return handler

    def _add_event_listener(self, event, listener):
        self._listeners[event] = listener
        return listener

    async def __call__(self, scope, receive, send):
        if scope['type'] == 'http':
            await self.http_handler(scope, receive, send)
        elif scope['type'] == 'lifespan':
            await self.lifespan_handler(scope, receive, send)

    async def http_handler(self, scope, receive, send):
        response = await self._handle_request(scope, receive)

        await send({
            'type': 'http.response.start',
            'status': response.status,
            'headers': [(k.encode(), v.encode()) for k, v in response.headers],
        })
        await send({
            'type': 'http.response.body',
            'body': response.body,
        })

    async def _handle_request(self, scope, receive):
        match = self._match(scope['path'])
        if match is None:
            return Response(status=404)

        method, handler, params = match
        if method != scope['method']:
            return Response(status=405)

        request = Request(
            path=scope['path'],
            method=scope['method'],
            headers=CaselessMultiDict(scope['headers']),
            query=MultiDict(parse_qsl(scope['query_string'])),
            body=await self._read_request_body(receive),
        )
        return await handler(request, **params)

    def _match(self, request_path):
        for path, method, handler in self._routes:
            m = path.match(request_path)
            if m is not None:
                return method, handler, m.groupdict()

    @staticmethod
    async def _read_request_body(receive):
        body = bytearray()
        while True:
            msg = await receive()
            body += msg['body']
            if not msg.get('more_body'):
                break
        return bytes(body)

    async def lifespan_handler(self, scope, receive, send):
        while True:
            msg = await receive()
            msg_type = msg['type'].split('.')[-1]
            listener = self._listeners.get(msg_type)
            if listener is not None:
                try:
                    await listener()
                except Exception:
                    await send({'type': f'lifespan.{msg_type}.failed'})
                    raise

            await send({'type': f'lifespan.{msg_type}.complete'})

            if msg_type == 'shutdown':
                break
