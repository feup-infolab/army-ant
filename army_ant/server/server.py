import aiohttp, aiohttp_jinja2, jinja2, asyncio, math, time, tempfile, os, json, logging, yaml
from jpype import *
from datetime import datetime
from jpype import *
from datetime import datetime
from collections import OrderedDict
from aiohttp import web
from aiohttp.client_exceptions import ClientOSError
from army_ant.index import Index, Result
from army_ant.database import Database
from army_ant.evaluation import EvaluationTask, EvaluationTaskManager
from army_ant.util import set_dict_defaults
from army_ant.exception import ArmyAntException

logger = logging.getLogger(__name__)

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

    ranking_function = request.GET.get('ranking_function')
    if ranking_function is None:
        ranking_function = request.app['engines'][engine].get('ranking', {}).get('default', {}).get('id')

    ranking_params = {}
    for k in request.GET.keys():
        if k.startswith('ranking_param_'):
            _, _, param_name = k.split('_')
            param_value = request.GET.get(k)
            ranking_params[param_name] = param_value

    debug = request.GET.get('debug', 'off')

    query = request.GET.get('query')
    error = None
    trace = None
    trace_ascii = None
    offset = 0
    limit = 30 if debug == 'on' else 5

    if query:
        offset = int(request.GET.get('offset', str(offset)))
        limit = int(request.GET.get('limit', str(limit)))
        try:
            loop = asyncio.get_event_loop()
            index = Index.open(
                request.app['engines'][engine]['index']['location'],
                request.app['engines'][engine]['index']['type'],
                loop)
            engine_response = await index.search(query, offset, limit, ranking_function, ranking_params)

            num_docs = len(engine_response['results'])
            if engine_response['numDocs']: num_docs = engine_response['numDocs']
            if type(num_docs) is java.lang.Long: num_docs = num_docs.longValue()

            if 'trace' in engine_response: trace = engine_response['trace']
            if 'traceASCII' in engine_response: trace_ascii = engine_response['traceASCII']

            results = engine_response['results']
            page = int((offset+limit) / limit)
            pages = math.ceil(num_docs / limit)
            
            db = Database.factory(
                request.app['engines'][engine]['db']['location'],
                request.app['engines'][engine]['db']['name'],
                request.app['engines'][engine]['db']['type'],
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
            'rankingFunction': ranking_function,
            'rankingParams': ranking_params,
            'query': query,
            'debug': debug,
            'time': end_time - start_time,
            'offset': offset,
            'limit': limit,
            'numDocs': num_docs,
            'page': page,
            'pages': pages,
            'results': results,
            'metadata': metadata,
            'trace': trace,
            'trace_ascii': trace_ascii
        }

    fmt = request.GET.get('format', 'html')
    if fmt == 'json':
        return web.json_response(response, dumps = lambda obj: json.dumps(obj, default=serialize_json))
    else:
        return response

async def evaluation_get(request):
    manager = EvaluationTaskManager(
        request.app['defaults']['db']['location'],
        request.app['defaults']['db']['name'],
        request.app['defaults']['eval']['location'])
    tasks = manager.get_tasks()
    metrics = set([])
    for task in tasks:
        if hasattr(task, 'results'):
            metrics = metrics.union([metric for metric in task.results.keys()])
    return { 'tasks': tasks, 'metrics': sorted(metrics) }

async def evaluation_delete(request):
    manager = EvaluationTaskManager(
        request.app['defaults']['db']['location'],
        request.app['defaults']['db']['name'],
        request.app['defaults']['eval']['location'])
    task_id = request.GET.get('task_id')

    success = False
    if task_id: success = manager.del_task(task_id)

    if success:
        return web.json_response({ 'success': "Deleted task with task_id = %s." % task_id })
    return web.json_response({ 'error': "Could not delete task with task_id = %s." % task_id }, status=404)

async def evaluation_reset(request):
    manager = EvaluationTaskManager(
        request.app['defaults']['db']['location'],
        request.app['defaults']['db']['name'],
        request.app['defaults']['eval']['location'])
    task_id = request.GET.get('task_id')

    success = False
    if task_id: success = manager.reset_task(task_id)

    if success:
        return web.json_response({ 'success': "Reset task with task_id = %s to WAITING status." % task_id })
    return web.json_response({ 'error': "Could not reset task with task_id = %s to WAITING status." % task_id }, status=404)

async def evaluation_rename(request):
    manager = EvaluationTaskManager(
        request.app['defaults']['db']['location'],
        request.app['defaults']['db']['name'],
        request.app['defaults']['eval']['location'])
    task_id = request.GET.get('task_id')
    run_id = request.GET.get('run_id')

    success = False
    if task_id and run_id: success = manager.rename_task(task_id, run_id)

    if success: return web.json_response({ 'success': "Renamed Run ID of task %s to '%s'." % (task_id, run_id) })
    return web.json_response({ 'error': "Could not rename Run ID of task %s to '%s'." % (task_id, run_id) }, status=404)

async def evaluation_post(request):
    data = await request.post()

    if len(data['topics']) > 0:
        with tempfile.NamedTemporaryFile(dir=os.path.join(request.app['defaults']['eval']['location'], 'spool'),
                                         prefix='eval_topics_', delete=False) as fp:
            fp.write(data['topics'].file.read())
            topics_filename = data['topics'].filename
            topics_path = fp.name
    else:
        topics_filename = None
        topics_path = None

    if len(data['assessments']) > 0:
        with tempfile.NamedTemporaryFile(dir=os.path.join(request.app['defaults']['eval']['location'], 'spool'),
                                         prefix='eval_assessments_', delete=False) as fp:
            fp.write(data['assessments'].file.read())
            assessments_filename = data['assessments'].filename
            assessments_path = fp.name
    else:
        assessments_filename = None
        assessments_path = None

    manager = EvaluationTaskManager(
        request.app['defaults']['db']['location'],
        request.app['defaults']['db']['name'],
        request.app['defaults']['eval']['location'])

    index_location = request.app['engines'][data['engine']]['index']['location']
    index_type = request.app['engines'][data['engine']]['index']['type']
    ranking_function = request.app['engines'][data['engine']].get('ranking', {}).get('default', {}).get('id')

    manager.add_task(EvaluationTask(
        index_location,
        index_type,
        data['eval-format'],
        ranking_function,
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

async def evaluation_download(request):
    headers = request.GET.get('headers')
    metrics = request.GET.get('metrics')
    if metrics is None: return web.HTTPNotFound()

    headers = headers.split(',') if headers else None
    metrics = metrics.split(',')
    decimals = int(request.GET.get('decimals', '4'))
    fmt = request.GET.get('fmt', 'csv')

    manager = EvaluationTaskManager(
        request.app['defaults']['db']['location'],
        request.app['defaults']['db']['name'],
        request.app['defaults']['eval']['location'])

    try:
        with manager.get_results_summary(headers, metrics, decimals, fmt) as f:
            timestamp = datetime.now().strftime('%Y%m%dT%H%M%S')
            response = web.StreamResponse(headers={
                'Content-Disposition': 'attachment; filename="metrics-%s.%s"' % (timestamp, fmt)
            })
            await response.prepare(request)

            f.seek(0)
            response.write(f.read())
            response.write_eof()
            await response.drain()

            return response
    except FileNotFoundError:
        return web.HTTPNotFound()
 
async def evaluation_results_archive(request):
    task_id = request.GET.get('task_id')
    if task_id is None: return web.HTTPNotFound()

    manager = EvaluationTaskManager(
        request.app['defaults']['db']['location'],
        request.app['defaults']['db']['name'],
        request.app['defaults']['eval']['location'])

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

    manager = EvaluationTaskManager(
        request.app['defaults']['db']['location'],
        request.app['defaults']['db']['name'],
        request.app['defaults']['eval']['location'])

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
    elif request.method == 'DELETE':
        return await evaluation_delete(request)

@aiohttp_jinja2.template('about.html')
async def about(request):
    pass

async def start_background_tasks(app):
    logger.info("Starting background tasks")
    manager = EvaluationTaskManager(
        app['defaults']['db']['location'],
        app['defaults']['db']['name'],
        app['defaults']['eval']['location'])
    app['evaluation_queue_listener'] = app.loop.create_task(manager.process())

async def cleanup_background_tasks(app):
    logger.info("Stopping background tasks")
    app['evaluation_queue_listener'].cancel()
    await app['evaluation_queue_listener']

async def shutdown_jvm(app):
    logger.info("Shutting down JVM")
    if isJVMStarted(): shutdownJVM()

async def preload_engines(app):
    logger.info("Preloading engines")
    for engine, config in app['engines'].items():
        preload = config['index'].get('preload', False)
        if preload:
            if 'preloaded_engines' in app:
                if 'engine' in app['preloaded_engines']: continue
            else:
                app['preloaded_engines'] = {}

            loop = asyncio.get_event_loop()
            await Index.preload(
                app['engines'][engine]['index']['location'],
                app['engines'][engine]['index']['type'],
                loop)

def run_app(loop, host, port, path=None):
    config = yaml.load(open('config.yaml'))

    app = web.Application(client_max_size=1024*1024*4, loop=loop)

    app['defaults'] = config.get('defaults', {})
    app['engines'] = config.get('engines', [])
    for engine in app['engines']:
        if 'message' in app['engines'][engine]:
            logger.warn("%s: %s" % (engine, app['engines'][engine]['message']))
        set_dict_defaults(app['engines'][engine], app['defaults'])

    if not 'db' in app['defaults']: app['defaults']['db'] = {}
    if not 'location' in app['defaults']['db']: app['defaults']['db'] = 'localhost'

    if not 'eval' in app['defaults']: app['defaults']['eval'] = {}
    if not 'location' in app['defaults']['eval']: app['defaults']['eval']['location'] = tempfile.gettempdir()

    aiohttp_jinja2.setup(
        app,
        loader=jinja2.FileSystemLoader('army_ant/server/templates'),
        filters = { 'timestamp_to_date': timestamp_to_date },
        context_processors=[page_link, aiohttp_jinja2.request_processor])

    app.router.add_get('/', home, name='home')
    app.router.add_get('/search', search, name='search')
    app.router.add_get('/evaluation', evaluation, name='evaluation')
    app.router.add_post('/evaluation', evaluation)
    app.router.add_delete('/evaluation', evaluation, name='evaluation_delete')
    app.router.add_put('/evaluation/reset', evaluation_reset, name='evaluation_reset')
    app.router.add_put('/evaluation/rename', evaluation_rename, name='evaluation_rename')
    app.router.add_get('/evaluation/download', evaluation_download, name='evaluation_download')
    app.router.add_get('/evaluation/results/archive', evaluation_results_archive, name='evaluation_results_archive')
    app.router.add_get('/evaluation/results/ll-api', evaluation_results_ll_api, name='evaluation_results_ll_api')
    app.router.add_get('/about', about, name='about')

    app.router.add_static('/static', 'army_ant/server/static', name='static', follow_symlinks=True)

    app.on_startup.append(start_background_tasks)
    app.on_startup.append(preload_engines)
    app.on_cleanup.append(shutdown_jvm)
    app.on_cleanup.append(cleanup_background_tasks)

    if path:
        os.umask(0o000)
        web.run_app(app, path=path)
    else:
        web.run_app(app, host=host, port=port)

