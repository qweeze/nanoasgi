### nanoasgi

#### Usage:
```python
from nanoasgi import App

app = App()

@app.on('startup')
async def on_startup():
    ...

@app.on('shutdown')
async def on_shutdown():
    ...

@app.route('GET', '/api/hello/{name}/')
async def hello_handler(request, name):
    return Response(
        {'result': f'Hello {name}!'},
        status=200,
        headers=[('Content-Type', 'application/json')],
    )
```
