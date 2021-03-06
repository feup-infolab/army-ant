#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# army-ant.py
# José Devezas (joseluisdevezas@gmail.com)
# 2017-03-09

import asyncio
import logging
import os
import re
import readline
import shutil
import tempfile

import fire
import yaml

from army_ant.analysis import rank_correlation, rws_rank_concordance
from army_ant.database import Database
from army_ant.evaluation import EvaluationTask, EvaluationTaskManager
from army_ant.exception import ArmyAntException
from army_ant.extras import fetch_wikipedia_images, word2vec_knn, word2vec_sim
from army_ant.features import FeatureExtractor
from army_ant.index import Index
from army_ant.reader import Reader
from army_ant.sampling import INEXSampler
from army_ant.server import run_app
from army_ant.setup import config_logger
from army_ant.util.dbpedia import DBpediaClass, fetch_dbpedia_entity_labels

config_logger(logging.INFO)


logger = logging.getLogger(__name__)


class CommandLineInterfaceAnalysis(object):
    def rank_concordance(self, index_location, index_type, rw_length, rw_repeats, topics_path, output_path,
                         cutoff=1000, repeats=100, method='kendall_w', force=False):
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(
                rws_rank_concordance(index_location, index_type, rw_length, rw_repeats, topics_path, output_path,
                                     cutoff, repeats, method, force, loop))
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

    def rank_correlation(self, index_a_location, index_a_type, index_b_location, index_b_type,
                         ranking_function_a, ranking_function_b, topics_path, output_path,
                         ranking_params_a="", ranking_params_b="", cutoff=1000, repeats=100,
                         method='spearman', force=False):
        try:
            ranking_params_a = dict(tuple(param.split('=')) for param in ranking_params_a.split(','))
        except Exception:
            logger.warning("Empty ranking parameters for %s" % ranking_function_a)
            ranking_params_a = {}

        try:
            ranking_params_b = dict(tuple(param.split('=')) for param in ranking_params_b.split(','))
        except Exception:
            logger.warning("Empty ranking parameters for %s" % ranking_function_b)
            ranking_params_b = {}

        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(
                rank_correlation(index_a_location, index_a_type, index_b_location, index_b_type,
                                 ranking_function_a, ranking_function_b, ranking_params_a, ranking_params_b,
                                 topics_path, output_path, cutoff, repeats, method, force, loop))
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()


class CommandLineInterfaceSampling(object):
    def inex(self, qrels_input_path, qrels_output_path, topics_input_path, topics_output_path,
             corpus_input_path, corpus_output_path, include_linked=False, query_sample_size=None):
        try:
            s = INEXSampler(
                qrels_input_path, qrels_output_path, topics_input_path, topics_output_path,
                corpus_input_path, corpus_output_path, include_linked, query_sample_size)
            s.sample()
        except ArmyAntException as e:
            logger.error(e)


class CommandLineInterfaceExtras(object):
    def fetch_wikipedia_images(self, db_name, db_location='localhost', db_type='mongo'):
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(fetch_wikipedia_images(db_location, db_name, db_type, loop))
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

    def word2vec_knn(self, model_path, word, k=5):
        knn = word2vec_knn(model_path, word, k)
        if knn is None:
            print("No results found")
            return

        rank = 1
        for word, score in knn:
            print(rank, '\t', score, '\t', word)
            rank += 1

    def word2vec_sim(self, model_path, word1, word2):
        sim = word2vec_sim(model_path, word1, word2)
        if sim is None:
            print("Could not calculate similarity: one of the words was not found")
            return

        print(word1, '~', word2, '=', sim)

    def fetch_dbpedia_entities(self, class_name, output_location, lang='en'):
        limit = 10_000
        offset = 0
        count = 0

        with open(output_location, 'w') as f:
            while True:
                logger.info(
                    "Fetching DBpedia entities of class %s (offset=%s, limit=%s)" % (class_name, offset, limit))

                entities = fetch_dbpedia_entity_labels(DBpediaClass[class_name], lang=lang, offset=offset, limit=limit)

                if len(entities) < 1:
                    break
                count += len(entities)

                for entity in entities:
                    f.write("%s\n" % entity)
                    f.flush()

                offset += limit

        logger.info("Wrote %d entities of class %s (%s) to %s" % (
            count, DBpediaClass[class_name], class_name, output_location))


class SimpleCompleter(object):
    def __init__(self, options):
        self.options = sorted(options)

    def complete(self, text, state):
        if state == 0:
            if text:
                self.matches = [s for s in self.options if s and s.startswith(text)]
            else:
                self.matches = self.options[:]

        try:
            return self.matches[state]
        except IndexError:
            return None


class CommandLineInterface(object):
    def __init__(self):
        self.extras = CommandLineInterfaceExtras()
        self.sampling = CommandLineInterfaceSampling()
        self.analysis = CommandLineInterfaceAnalysis()

    def index(self, source_path, source_reader, index_location, index_type, features_location=None,
              db_location='localhost', db_name=None, db_type='mongo', limit=None):
        try:
            reader = Reader.factory(source_path, source_reader, features_location=features_location, limit=limit)

            loop = asyncio.get_event_loop()
            try:
                index = Index.factory(reader, index_location, index_type, loop)
                if db_location and db_name and db_type:
                    db = Database.factory(db_location, db_name, db_type, loop)
                    loop.run_until_complete(db.store(index.index(features_location=features_location)))
                else:
                    loop.run_until_complete(Index.no_store(index.index(features_location=features_location)))
            finally:
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()
        except ArmyAntException as e:
            logger.error(e)

    def search(self, index_location, index_type, query_type=None, task=None,
               base_index_location=None, base_index_type=None, ranking_function=None, ranking_params=None,
               db_location='localhost', db_name=None, db_type='mongo', query=None, offset=0, limit=10,
               interactive=False):
        if query is None and not interactive:
            logger.error("Must either use --query or --interactive")
            return

        if interactive:
            completer = SimpleCompleter([r'\quit', r'\set_ranking_random_walk', r'\set_ranking_biased_random_walk'])
            readline.parse_and_bind("tab: complete")
            readline.set_completer(completer.complete)
            readline.set_completer_delims(readline.get_completer_delims().replace('\\', ''))

        try:
            loop = asyncio.get_event_loop()
            while True:
                try:
                    if interactive:
                        query = input('query> ')
                        if query == r'\quit':
                            break
                        if query.strip() == '':
                            continue

                        ranking = re.match(r'\\set_ranking_(.*)', query)
                        if ranking:
                            ranking_function = ranking.group(1)
                            print("==> Switched to '%s' ranking function" % ranking_function)
                            continue

                    try:
                        ranking_params = dict(tuple(param.split('=')) for param in ranking_params.split(','))
                    except Exception:
                        logger.warning("Empty ranking parameters for %s" % ranking_function)
                        ranking_params = {}

                    index = Index.open(index_location, index_type, loop)
                    response = loop.run_until_complete(index.search(
                        query, offset, limit, query_type=query_type, task=task,
                        base_index_location=base_index_location, base_index_type=base_index_location,
                        ranking_function=ranking_function, ranking_params=ranking_params))

                    if db_location and db_name and db_type:
                        db = Database.factory(db_location, db_name, db_type, loop)
                        metadata = loop.run_until_complete(db.retrieve(response['results']))
                    else:
                        metadata = []

                    for (result, i) in zip(response['results'], range(offset, offset + limit)):
                        print(
                            "==> %3d %7.2f [%s] %s" % (
                                i + 1, result['score'], result['type'],
                                result['name'] if result['name'] else result['id']))
                        doc_id = result['id']
                        if doc_id in metadata:
                            for item in metadata[doc_id].items():
                                print("\t%10s: %s" % item)
                            print()
                except ArmyAntException as e:
                    logger.error(e)
                except (EOFError, KeyboardInterrupt):
                    print("\\quit")
                    break

                if not interactive:
                    break
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

    def inspect(self, index_location, index_type, workdir='.', feature=None, interactive=False):
        if feature is None and not interactive:
            logger.error("Must either use --feature or --interactive")
            return

        if interactive:
            completer = SimpleCompleter(
                [r'\quit', 'summary', 'synonym-summary', 'context-summary', 'list-nodes', 'list-hyperedges'])
            readline.parse_and_bind("tab: complete")
            readline.set_completer(completer.complete)
            readline.set_completer_delims(readline.get_completer_delims().replace('\\', ''))

        try:
            loop = asyncio.get_event_loop()
            while True:
                try:
                    if interactive:
                        feature = input('feature> ')
                        if feature == r'\quit':
                            break
                        if feature.strip() == '':
                            continue

                    index = Index.open(index_location, index_type, loop)
                    loop.run_until_complete(index.inspect(feature, workdir))
                except ArmyAntException as e:
                    logger.error(e)
                except (EOFError, KeyboardInterrupt):
                    print("\\quit")
                    break

                if not interactive:
                    break
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

    def evaluation(self, index_location, index_type, eval_format, topics_filename=None, assessments_filename=None,
                   base_url=None, api_key=None, run_id=None, output_dir='/opt/army-ant/eval'):
        if eval_format == 'inex' and (topics_filename is None or assessments_filename is None):
            raise ArmyAntException("Must include the arguments --topics-filename and --assessments-filename")

        if eval_format == 'll-api' and (base_url is None or api_key is None or run_id is None):
            raise ArmyAntException("Must include the arguments --base-url, --api-key and --run-id")

        if eval_format == 'inex':
            spool_dir = os.path.join(output_dir, 'spool')

            with open(topics_filename, 'rb') as fsrc, \
                    tempfile.NamedTemporaryFile(dir=spool_dir, prefix='eval_topics_', delete=False) as fdst:
                shutil.copyfileobj(fsrc, fdst)
                topics_path = fdst.name

            with open(assessments_filename, 'rb') as fsrc, \
                    tempfile.NamedTemporaryFile(dir=spool_dir, prefix='eval_assessments_', delete=False) as fdst:
                shutil.copyfileobj(fsrc, fdst)
                assessments_path = fdst.name
        else:
            topics_path = None
            assessments_path = None

        # TODO must add query_type, base_indexes, ranking_function and ranking_params
        task = EvaluationTask(
            index_location=index_location,
            index_type=index_type,
            eval_format=eval_format,
            query_type=None,
            base_indexes=None,
            ranking_function=None,
            ranking_params=None,
            topics_filename=topics_filename,
            topics_path=topics_path,
            assessments_filename=assessments_filename,
            assessments_path=assessments_path,
            base_url=base_url,
            api_key=api_key,
            run_id=run_id)

        config = yaml.load(open('config.yaml'))
        db_location = config['default'].get('db', {}).get('location', 'localhost')
        db_name = config['default'].get('db', {}).get('name', 'army_ant')
        manager = EvaluationTaskManager(db_location, db_name, output_dir)

        manager.add_task(task)
        inserted_ids = manager.queue()
        if len(inserted_ids) < 1:
            raise ArmyAntException("Could not queue task")

        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(manager.process(task_id=inserted_ids[0]))
        except KeyboardInterrupt:
            for task in asyncio.Task.all_tasks():
                task.cancel()
        finally:
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

    def features(self, method, source_path, source_reader, output_location):
        reader = Reader.factory(source_path, source_reader)
        fe = FeatureExtractor.factory(method, reader, output_location)
        fe.extract()

    def server(self, host='127.0.0.1', port=8080, path=None):
        loop = asyncio.get_event_loop()
        run_app(loop, host, port, path)


if __name__ == '__main__':
    fire.Fire(CommandLineInterface)
