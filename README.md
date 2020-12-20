### nanoasgi
This is a toy ASGI web framework. It has zero dependencies and only 170 lines of code. I wrote it to play around with ASGI and to study how frameworks work under the hood.
Python >= 3.7 is required.

#### Example:
```python
# example.py
from nanoasgi import App


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
```
```bash
$ uvicorn example:app
```
