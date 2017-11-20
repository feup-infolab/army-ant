import aiohttp, aiohttp_jinja2, jinja2, asyncio, configparser, math, time, tempfile, os, json
from jpype import *
from datetime import datetime
from collections import OrderedDict
from aiohttp import web
from aiohttp.errors import ClientOSError
from army_ant.index import Index, Result
from army_ant.database import Database
from army_ant.evaluation import EvaluationTask, EvaluationTaskManager
from army_ant.exception import ArmyAntException

async def page_link(request):
    def _page_link(page, limit):
        query = dict(request.url.query)
        offset = (page - 1) * limit
        if offset < 0: offset = 0
        query['offset'] = offset
        return request.url.with_query(query)
    return { 'page_link': _page_link }

def timestamp_to_date(timestamp):
    return datetime.fromtimestamp(int(round(timestamp / 1000)))

def serialize_json(obj):
    if isinstance(obj, Result):
        return obj.__dict__
    return obj

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

            num_docs = len(engine_response['results'])
            if engine_response['numDocs']: num_docs = engine_response['numDocs'].longValue()

            results = engine_response['results']
            page = int((offset+limit) / limit)
            pages = math.ceil(num_docs / limit)
            
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
        return web.json_response(response, dumps = lambda obj: json.dumps(obj, default=serialize_json))
    else:
        return response

async def evaluation_get(request):
    manager = EvaluationTaskManager(request.app['db_location'], request.app['default_eval_location'])
    return { 'tasks': manager.get_tasks() }

async def evaluation_post(request):
    data = await request.post()

    if len(data['topics']) > 0:
        with tempfile.NamedTemporaryFile(dir=os.path.join(request.app['default_eval_location'], 'spool'), prefix='eval_topics_', delete=False) as fp:
            fp.write(data['topics'].file.read())
            topics_filename = data['topics'].filename
            topics_path = fp.name
    else:
        topics_filename = None
        topics_path = None

    if len(data['assessments']) > 0:
        with tempfile.NamedTemporaryFile(dir=os.path.join(request.app['default_eval_location'], 'spool'), prefix='eval_assessments_', delete=False) as fp:
            fp.write(data['assessments'].file.read())
            assessments_filename = data['assessments'].filename
            assessments_path = fp.name
    else:
        assessments_filename = None
        assessments_path = None

    manager = EvaluationTaskManager(request.app['db_location'], request.app['default_eval_location'])

    if data['engine'] == '__all__':
        for engine in request.app['engines']:
            index_location = request.app['engines'][engine]['index_location']
            index_type = request.app['engines'][engine]['index_type']

            manager.add_task(EvaluationTask(
                index_location,
                index_type,
                data['eval-format'],
                topics_filename,
                topics_path,
                assessments_filename,
                assessments_path,
                data['base-url'],
                data['api-key'],
                data['run-id']))
    else:
        index_location = request.app['engines'][data['engine']]['index_location']
        index_type = request.app['engines'][data['engine']]['index_type']

        manager.add_task(EvaluationTask(
            index_location,
            index_type,
            data['eval-format'],
            topics_filename,
            topics_path,
            assessments_filename,
            assessments_path,
            data['base-url'],
            data['api-key'],
            data['run-id']))

    error = None
    try:
        manager.queue()
    except ArmyAntException as e:
        error = str(e)

    response = await evaluation_get(request)
    if error: response['error'] = error

    return response

async def evaluation_results_archive(request):
    task_id = request.GET.get('task_id')
    if task_id is None: return web.HTTPNotFound()

    manager = EvaluationTaskManager(request.app['db_location'], request.app['default_eval_location'])
    try:
        with manager.get_results_archive(task_id) as archive_filename:
            response = web.StreamResponse(headers={ 'Content-Disposition': 'attachment; filename="%s.zip"' % task_id })
            await response.prepare(request)

            with open(archive_filename, 'rb') as f:
                response.write(f.read())
            response.write_eof()
            await response.drain()

            return response
    except FileNotFoundError:
        return web.HTTPNotFound()
 
@aiohttp_jinja2.template('ll_api_outcome.html')
async def evaluation_results_ll_api(request):
    task_id = request.GET.get('task_id')
    if task_id is None: return web.HTTPNotFound()

    manager = EvaluationTaskManager(request.app['db_location'], request.app['default_eval_location'])
    data = manager.get_results_json(task_id)

    fmt = request.GET.get('fmt', 'json')
    if fmt == 'html': return data
    return web.json_response(data)
 
@aiohttp_jinja2.template('evaluation.html')
async def evaluation(request):
    if request.method == 'GET':
        return await evaluation_get(request)
    elif request.method == 'POST':
        return await evaluation_post(request)

@aiohttp_jinja2.template('about.html')
async def about(request):
    pass

async def start_background_tasks(app):
    manager = EvaluationTaskManager(app['db_location'], app['default_eval_location'])
    app['evaluation_queue_listener'] = app.loop.create_task(manager.process())

async def cleanup_background_tasks(app):
    app['evaluation_queue_listener'].cancel()
    await app['evaluation_queue_listener']

async def shutdown_jvm(app):
    if isJVMStarted(): shutdownJVM()

async def preload_engines(app):
    for engine, config in app['engines'].items():
        config['preload'] = config['preload'] == 'True'
        if config['preload']:
            if 'preloaded_engines' in app:
                if 'engine' in app['preloaded_engines']: continue
            else:
                app['preloaded_engines'] = {}

            loop = asyncio.get_event_loop()
            await Index.preload(
                app['engines'][engine]['index_location'],
                app['engines'][engine]['index_type'],
                loop)

def run_app(loop):
    config = configparser.ConfigParser()
    config.read('server.cfg')

    app = web.Application(loop=loop)

    app['engines'] = OrderedDict()
    for section in config.sections():
        app['engines'][section] = dict(config[section])
    app['db_location'] = config['DEFAULT'].get('db_location', 'localhost')
    app['default_eval_location'] = config['DEFAULT'].get('eval_location', tempfile.gettempdir())

    aiohttp_jinja2.setup(
        app,
        loader=jinja2.FileSystemLoader('army_ant/server/templates'),
        filters = { 'timestamp_to_date': timestamp_to_date },
        context_processors=[page_link, aiohttp_jinja2.request_processor])

    app.router.add_get('/', home, name='home')
    app.router.add_get('/search', search, name='search')
    app.router.add_get('/evaluation', evaluation, name='evaluation')
    app.router.add_post('/evaluation', evaluation)
    app.router.add_get('/evaluation/results/archive', evaluation_results_archive, name='evaluation_results_archive')
    app.router.add_get('/evaluation/results/ll-api', evaluation_results_ll_api, name='evaluation_results_ll_api')
    app.router.add_get('/about', about, name='about')

    app.router.add_static('/static', 'army_ant/server/static', name='static', follow_symlinks=True)

    app.on_startup.append(preload_engines)
    app.on_startup.append(start_background_tasks)
    app.on_cleanup.append(cleanup_background_tasks)    
    app.on_cleanup.append(shutdown_jvm)

    web.run_app(app)
