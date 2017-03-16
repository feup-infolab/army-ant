import aiohttp_jinja2, jinja2, asyncio
from aiohttp import web
from army_ant.index import Index

@aiohttp_jinja2.template('index.html')
async def index(request):
    query = request.GET.get('query')
    if query:
        index = Index.open('localhost', 'gow')
        results = loop.run_until_complete(index.search_async(query))
    else:
        results = []

    fmt = request.GET.get('format', 'html')
    if fmt == 'json':
        return jsonify(results)
    else:
        return { 'results': results }

def run_app(loop):
    app = web.Application(loop=loop)
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('army_ant/server/templates'))

    app.router.add_get('/', index)
    web.run_app(app)
