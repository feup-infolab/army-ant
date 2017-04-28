import aiohttp_jinja2, jinja2, asyncio, configparser, math
from collections import OrderedDict
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
        offset = int(request.GET.get('offset', "0"))
        limit = int(request.GET.get('limit', "10"))
        try:
            loop = asyncio.get_event_loop()
            index = Index.open(request.app['engines'][engine]['index_location'], engine, loop)
            engine_response = await index.search(query, offset, limit)

            results = engine_response['results']
            num_docs = engine_response['numDocs']
            page = int((offset+limit) / limit) 
            pages = math.ceil(engine_response['numDocs'] / limit)
            
            db = Database.factory(
                request.app['engines'][engine]['db_location'],
                request.app['engines'][engine]['db_name'],
                request.app['engines'][engine]['db_type'],
                loop)
            metadata = await db.retrieve(results)
        except (ArmyAntException, ClientOSError) as e:
            error = e
    else:
        results = []
        num_docs = 0
        page = None
        pages = None
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
            'offset': offset,
            'limit': limit,
            'numDocs': num_docs,
            'page': page,
            'pages': pages,
            'results': results,
            'metadata': metadata
        }

    fmt = request.GET.get('format', 'html')
    if fmt == 'json':
        return web.json_response(response)
    else:
        return response

def run_app(loop):
    config = configparser.ConfigParser()
    config.read('server.cfg')

    app = web.Application(loop=loop)

    app['engines'] = OrderedDict()
    for section in config.sections():
        if section != 'DEFAULT':
            app['engines'][section] = dict(config[section])

    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('army_ant/server/templates'))

    app.router.add_get('/', search)
    app.router.add_static('/static', 'army_ant/server/static', name='static', follow_symlinks=True)
    web.run_app(app)
