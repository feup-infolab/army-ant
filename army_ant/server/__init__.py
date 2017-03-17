import aiohttp_jinja2, jinja2, asyncio
from aiohttp import web
from army_ant.index import Index
from army_ant.exception import ArmyAntException

@aiohttp_jinja2.template('index.html')
async def index(request):
    engine = request.GET.get('engine')
    if engine is None: engine = 'gow'

    query = request.GET.get('query')
    error = None
    if query:
        try:
            loop = asyncio.get_event_loop()
            index = Index.open('localhost', engine, loop)
            results = await index.search(query)
        except ArmyAntException as e:
            error = e
    else:
        results = {}

    debug = request.GET.get('debug', 'off')

    if error:
        response = {
            'engine': engine,
            'query': query,
            'debug': debug,
            'error': str(error)
        }
    else:
        response = {
            'engine': engine,
            'query': query,
            'debug': debug,
            'results': results
        }

    fmt = request.GET.get('format', 'html')
    if fmt == 'json':
        return web.json_response(response)
    else:
        return response

def run_app(loop):
    app = web.Application(loop=loop)
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('army_ant/server/templates'))

    app.router.add_get('/', index)
    app.router.add_static('/static', 'army_ant/server/static', name='static', follow_symlinks=True)
    web.run_app(app)
