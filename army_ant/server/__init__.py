import asyncio
from flask import Flask, request, render_template
from flask.json import jsonify

from army_ant.index import Index

app = Flask(__name__)

@app.route('/')
def index():
    query = request.args.get('query')
    if query:
        index = Index.open('localhost', 'gow')
        loop = asyncio.get_event_loop()
        results = loop.run_until_complete(index.search_async(query, loop))
    else:
        results = []

    fmt = request.args.get('format', 'html')
    if fmt == 'json':
        return jsonify(results)
    else:
        return render_template('index.html', results=results)
