import aiohttp, aiohttp_jinja2, jinja2, asyncio, configparser, math, time
from collections import OrderedDict
from aiohttp import web
from aiohttp.errors import ClientOSError
from army_ant.index import Index
from army_ant.database import Database
from army_ant.exception import ArmyAntException

async def page_link(request):
    def _page_link(page, limit):
        query = dict(request.url.query)
        offset = (page - 1) * limit
        if offset < 0: offset = 0
        query['offset'] = offset
        return request.url.with_query(query)
    return { 'page_link': _page_link}

@aiohttp_jinja2.template('home.html')
async def home(request):
    pass

@aiohttp_jinja2.template('search.html')
async def search(request):
    start_time = time.time()

    engine = request.GET.get('engine')
    if engine is None: engine = list(request.app['engines'].keys())[0]

    debug = request.GET.get('debug', 'off')

    query = request.GET.get('query')
    error = None
    offset = 0
    limit = 30 if debug == 'on' else 5

    if query:
        offset = int(request.GET.get('offset', str(offset)))
        limit = int(request.GET.get('limit', str(limit)))
        try:
            loop = asyncio.get_event_loop()
            index = Index.open(
                request.app['engines'][engine]['index_location'],
                request.app['engines'][engine]['index_type'],
                loop)
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

    end_time = time.time()

    if error:
        response = {
            'engine': engine,
            'query': query,
            'debug': debug,
            'time': end_time - start_time,
            'error': str(error)
        }
    else:
        response = {
            'engine': engine,
            'query': query,
            'debug': debug,
            'time': end_time - start_time,
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

@aiohttp_jinja2.template('evaluation.html')
async def evaluation(request):
    pass

@aiohttp_jinja2.template('evaluation.html')
async def evaluation_launch(request):
    reader = await request.multipart()
    print(reader.next())

    # /!\ Don't forget to validate your inputs /!\

    #mp3 = await reader.next()

    ##filename = mp3.filename

    ### You cannot rely on Content-Length if transfer is chunked.
    ##size = 0
    ##with open(os.path.join('/spool/yarrr-media/mp3/', filename), 'wb') as f:
        ##while True:
            ##chunk = await mp3.read_chunk()  # 8192 bytes by default.
            ##if not chunk:
                ##break
            ##size += len(chunk)
            ##f.write(chunk)

    #return web.Response(text='{} sized of {} successfully stored'
                        #''.format(filename, size))
    

@aiohttp_jinja2.template('about.html')
async def about(request):
    pass

def run_app(loop):
    config = configparser.ConfigParser()
    config.read('server.cfg')

    app = web.Application(loop=loop)

    app['engines'] = OrderedDict()
    for section in config.sections():
        if section != 'DEFAULT':
            app['engines'][section] = dict(config[section])

    aiohttp_jinja2.setup(
        app,
        loader=jinja2.FileSystemLoader('army_ant/server/templates'),
        context_processors=[page_link, aiohttp_jinja2.request_processor])

    app.router.add_get('/', home, name='home')
    app.router.add_get('/search', search, name='search')
    app.router.add_get('/evaluation', evaluation, name='evaluation')
    app.router.add_post('/evaluation', evaluation_launch)
    app.router.add_get('/about', about, name='about')

    app.router.add_static('/static', 'army_ant/server/static', name='static', follow_symlinks=True)
    web.run_app(app)
