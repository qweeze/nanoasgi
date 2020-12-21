# test_simple.py


from nanoasgi import App, Response
from async_asgi_testclient import TestClient
import pytest


app = App()


@app.on('startup')
async def on_startup():
    print('Ready to serve requests')


@app.on('shutdown')
async def on_shutdown():
    print('Shutting down')


@app.route('GET', '/api/hello/{name}/')
async def hello_handler(request, name):
    return Response(
        {'result': f'Hello {name}!'},
        status=200,
        headers=[('Content-Type', 'application/json')],
    )


@pytest.mark.asyncio
async def test_app():
    async with TestClient(app) as client:
        resp = await client.get('/api/hello/World/')
        assert resp.status_code == 200
        assert resp.json() == {'result': 'Hello World!'}
