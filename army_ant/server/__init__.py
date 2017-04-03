import aiohttp_jinja2, jinja2, asyncio
from aiohttp import web
from aiohttp.errors import ClientOSError
from army_ant.index import Index
from army_ant.database import Database
from army_ant.exception import ArmyAntException

@aiohttp_jinja2.template('search.html')
async def search(request):
    engine = request.GET.get('engine')
    if engine is None: engine = 'gow'

    query = request.GET.get('query')
    error = None
    if query:
        try:
            loop = asyncio.get_event_loop()
            index = Index.open(request.app['index_location'], engine, loop)
            results = await index.search(query)
            db = Database.factory(request.app['db_location'], request.app['db_name'], request.app['db_type'], loop)
            metadata = await db.retrieve(results)
        except (ArmyAntException, ClientOSError) as e:
            error = e
    else:
        results = {}
        metadata = {}

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
            'results': results,
            'metadata': metadata
        }

    fmt = request.GET.get('format', 'html')
    if fmt == 'json':
        return web.json_response(response)
    else:
        return response

def run_app(loop, index_location, db_location, db_name, db_type):
    app = web.Application(loop=loop)

    app['index_location'] = index_location
    app['db_location'] = db_location
    app['db_name'] = db_name
    app['db_type'] = db_type
    
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('army_ant/server/templates'))

    app.router.add_get('/', search)
    app.router.add_static('/static', 'army_ant/server/static', name='static', follow_symlinks=True)
    web.run_app(app)
