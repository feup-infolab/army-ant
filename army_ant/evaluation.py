#!/usr/bin/env python
# -*- coding: utf8 -*-
#
# evaluation.py
# José Devezas <joseluisdevezas@gmail.com>
# 2017-05-19

import json, time, pymongo, asyncio, logging, csv, os, shutil, gzip
import tempfile, zipfile, math, requests, requests_cache, pickle, itertools
from enum import IntEnum
from lxml import etree
from datetime import datetime
from contextlib import contextmanager
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from bson.objectid import ObjectId
from urllib.parse import urljoin
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError
from army_ant.index import Index
from army_ant.util import md5, get_first, zipdir
from army_ant.exception import ArmyAntException

logger = logging.getLogger(__name__)

class Evaluator(object):
    @staticmethod
    def factory(task, eval_location):
        if task.eval_format == 'inex':
            return INEXEvaluator(task, eval_location)
        elif task.eval_format == 'll-api':
            return LivingLabsEvaluator(task, eval_location)
        else:
            raise ArmyAntException("Unsupported evaluator format")

    def __init__(self, task, eval_location):
        self.task = task
        self.results = {}
        self.interrupt = False
        self.start_date = datetime.now()

    async def run(self):
        raise ArmyAntException("Unsupported evaluator format %s" % eval_format)

class FilesystemEvaluator(Evaluator):
    def __init__(self, task, eval_location):
        super().__init__(task, eval_location)

        self.o_results_path = os.path.join(eval_location, 'results', task._id)
        self.o_assessments_path = os.path.join(eval_location, 'assessments', task._id)
        
        #try:
            #os.makedirs(self.o_results_path)
        #except FileExistsError:
            #raise ArmyAntException("Results directory '%s' already exists" % self.o_results_path)

        #try:
            #os.makedirs(self.o_assessments_path)
        #except FileExistsError:
            #raise ArmyAntException("Assessments directory '%s' already exists" % self.o_assessments_path)

    def remove_output(self):
        shutil.rmtree(self.o_results_path)
        shutil.rmtree(self.o_assessments_path)

class INEXEvaluator(FilesystemEvaluator):
    def __init__(self, task, eval_location):
        super().__init__(task, eval_location)

        self.loop = asyncio.get_event_loop()
        self.index = Index.open(self.task.index_location, self.task.index_type, self.loop)

    def get_assessed_topic_ids(self):
        topic_ids = set([])
        with open(self.task.assessments_path, 'r') as f:
            for line in f:
                topic_id, _ = line.split(' ', 1)
                topic_ids.add(topic_id)
        return topic_ids

    def get_topic_assessments(self):
        logger.info("Loading topic assessments")

        topic_doc_judgements = {}

        with open(self.task.assessments_path, 'r') as f:
            for line in f:
                topic_id, _, doc_id, judgement, _ = line.split(' ', 4)
                if not topic_id in topic_doc_judgements:
                    topic_doc_judgements[topic_id] = {}
                topic_doc_judgements[topic_id][doc_id] = int(judgement)

        return topic_doc_judgements

    async def get_topic_results(self, filter=None):
        topic_doc_judgements = self.get_topic_assessments()

        topics = etree.parse(self.task.topics_path)
        
        for topic in topics.xpath('//topic'):
            if self.interrupt:
                logger.warn("Evaluation task was interruped")
                break

            topic_id = get_first(topic.xpath('@id'))

            if filter and not topic_id in filter:
                logger.warning("Skipping topic '%s'" % topic_id)
                continue
            
            query = get_first(topic.xpath('title/text()'))
            
            logger.info("Obtaining results for query '%s' of topic '%s' using '%s' index at '%s'" % (query, topic_id, self.task.index_type, self.task.index_location))
            engine_response = await self.index.search(query, 0, 10000)

            with open(os.path.join(self.o_results_path, '%s.csv' % topic_id), 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['rank', 'doc_id', 'relevant'])
                for i, result in zip(range(1, len(engine_response['results'])+1), engine_response['results']):
                    doc_id = result['docID']
                    relevant = topic_doc_judgements[topic_id][doc_id] > 0 if doc_id in topic_doc_judgements[topic_id] else False
                    writer.writerow([i, doc_id, relevant])

    def path_to_topic_id(self, path):
        return os.path.basename(os.path.splitext(path)[0])

    def f_score(self, precision, recall, beta=1):
        if precision == 0 and recall == 0: return 0
        return (1 + beta**2) * (precision * recall) / ((beta**2 * precision) + recall)
    
    def calculate_precision_recall(self):
        # topic_id -> doc_id -> num_relevant_chars
        topic_doc_judgements = self.get_topic_assessments()

        result_files = [
            os.path.join(self.o_results_path, f)
            for f in os.listdir(self.o_results_path)
            if os.path.isfile(os.path.join(self.o_results_path, f))]

        o_eval_details_file = os.path.join(self.o_assessments_path, 'precision_recall_per_topic.csv')

        with open(o_eval_details_file, 'w') as ef:
            writer = csv.writer(ef)
            writer.writerow(['topic_id', 'tp', 'fp', 'tn', 'fn', 'precision', 'recall', 'f0.5', 'f1', 'f2'])

            tps = []
            fps = []
            tns = []
            fns = []
            precisions = []
            recalls = []
            f_0_5_scores = []
            f_1_scores = []
            f_2_scores = []

            for result_file in result_files:
                topic_id = self.path_to_topic_id(result_file)

                with open(result_file, 'r') as rf:
                    reader = csv.DictReader(rf)
                    result_doc_ids = set([row['doc_id'] for row in reader])

                    tp = fp = tn = fn = 0

                    for doc_id, judgment in topic_doc_judgements.get(topic_id, {}).items():
                        relevant = judgment > 0
                        if relevant:
                            if doc_id in result_doc_ids:
                                tp += 1
                            else:
                                fn += 1
                        else:
                            if doc_id in result_doc_ids:
                                fp += 1
                            else:
                                tn += 1

                    tps.append(tp)
                    fps.append(fp)
                    tns.append(tn)
                    fns.append(fn)

                    logger.debug("%s - TP(%d) + FP(%d) + TN(%d) + FN(%d) = %d" % (topic_id, tp, fp, tn, fn, tp+fp+tn+fn))

                    precision = tp / (tp + fp)
                    precisions.append(precision)

                    recall = tp / (tp + fn)
                    recalls.append(recall)

                    f_0_5_score = self.f_score(precision, recall, beta=0.5)
                    f_0_5_scores.append(f_0_5_score)

                    f_1_score = self.f_score(precision, recall, beta=1)
                    f_1_scores.append(f_1_score)

                    f_2_score = self.f_score(precision, recall, beta=2)
                    f_2_scores.append(f_2_score)

                    writer.writerow([topic_id, tp, fp, tn, fn, precision, recall, f_0_5_score, f_1_score, f_2_score])

            self.results['Micro Avg Prec'] = sum(tps) / (sum(tps) + sum(fps))
            self.results['Micro Avg Rec'] = sum(tps) / (sum(tps) + sum(fns))
            self.results['Macro Avg Prec'] = sum(precisions) / len(precisions)
            self.results['Macro Avg Rec'] = sum(recalls) / len(recalls)

            self.results['Micro Avg F0_5'] = self.f_score(self.results['Micro Avg Prec'], self.results['Micro Avg Rec'], beta=0.5)
            self.results['Micro Avg F1'] = self.f_score(self.results['Micro Avg Prec'], self.results['Micro Avg Rec'], beta=1)
            self.results['Micro Avg F2'] = self.f_score(self.results['Micro Avg Prec'], self.results['Micro Avg Rec'], beta=2)

            self.results['Macro Avg F0_5'] = self.f_score(self.results['Macro Avg Prec'], self.results['Macro Avg Rec'], beta=0.5)
            self.results['Macro Avg F1'] = self.f_score(self.results['Macro Avg Prec'], self.results['Macro Avg Rec'], beta=1)
            self.results['Macro Avg F2'] = self.f_score(self.results['Macro Avg Prec'], self.results['Macro Avg Rec'], beta=2)

    def calculate_precision_at_n(self, n=10):
        result_files = [
            os.path.join(self.o_results_path, f)
            for f in os.listdir(self.o_results_path)
            if os.path.isfile(os.path.join(self.o_results_path, f))]

        o_eval_details_file = os.path.join(self.o_assessments_path, 'p_at_%d-precision_at_%d_per_topic.csv' % (n, n))

        with open(o_eval_details_file, 'w') as ef:
            writer = csv.writer(ef)
            writer.writerow(['topic_id', 'p_at_%d' % n])

            precisions_at_n = []
            for result_file in result_files:
                topic_id = self.path_to_topic_id(result_file)

                with open(result_file, 'r') as rf:
                    reader = csv.DictReader(rf)
                    results = []
                    for row in itertools.islice(reader, n):
                        results.append(row['relevant'] == 'True')

                    precision_at_n = results.count(True) / n
                    precisions_at_n.append(precision_at_n)
                    writer.writerow([topic_id, precision_at_n])

            self.results['P@%d' % n] = sum(precisions_at_n) / len(precisions_at_n)

    def calculate_mean_average_precision(self):
        result_files = [
            os.path.join(self.o_results_path, f)
            for f in os.listdir(self.o_results_path)
            if os.path.isfile(os.path.join(self.o_results_path, f))]

        o_eval_details_file = os.path.join(self.o_assessments_path, 'map_average_precision_per_topic.csv')

        with open(o_eval_details_file, 'w') as ef:
            writer = csv.writer(ef)
            writer.writerow(['topic_id', 'avg_precision'])

            avg_precisions = []
            for result_file in result_files:
                topic_id = self.path_to_topic_id(result_file)

                precisions = []
                with open(result_file, 'r') as rf:
                    reader = csv.DictReader(rf)
                    results = []
                    for row in reader:
                        results.append(row['relevant'] == 'True')

                    for i in range(1, len(results)+1):
                        rel = results[0:i]
                        p = sum(rel) / len(rel)
                        precisions.append(p)

                    avg_precision = 0.0 if len(precisions) == 0 else sum(precisions) / len(precisions)
                    avg_precisions.append(avg_precision)
                    writer.writerow([topic_id, avg_precision])

            self.results['MAP'] = sum(avg_precisions) / len(avg_precisions)

    def calculate_normalized_discounted_cumulative_gain_at_p(self, p=10):
        result_files = [
            os.path.join(self.o_results_path, f)
            for f in os.listdir(self.o_results_path)
            if os.path.isfile(os.path.join(self.o_results_path, f))]

        ndcgs = []
        for result_file in result_files:
            topic_id = self.path_to_topic_id(result_file)

            dcg_parcels = []
            idcg_parcels = []
            with open(result_file, 'r') as rf:
                reader = csv.DictReader(rf)
                results = []
                for row in reader:
                    results.append(row['relevant'] == 'True')

                for i in range(1, min(len(results), p) + 1):
                    rel = results[i-1]
                    dcg_p = rel / math.log2(i + 1)
                    dcg_parcels.append(dcg_p)

                for i in range(1, len(results)+1):
                    rel = results[i-1]
                    idcg_p = (2**rel - 1) / math.log2(i + 1)
                    idcg_parcels.append(idcg_p)

                ndcg = 0.0 if len(dcg_parcels) == 0 else sum(dcg_parcels) / len(idcg_parcels)
                ndcgs.append(ndcg)

        self.results['NDCG@%d' % p] = 0.0 if len(ndcgs) == 0 else sum(ndcgs) / len(ndcgs)

    async def run(self):
        assessed_topic_ids = self.get_assessed_topic_ids()
        await self.get_topic_results(assessed_topic_ids)
        self.calculate_precision_recall()
        self.calculate_precision_at_n(n=10)
        self.calculate_precision_at_n(n=100)
        self.calculate_precision_at_n(n=1000)
        self.calculate_mean_average_precision()
        self.calculate_normalized_discounted_cumulative_gain_at_p(p=10)
        self.calculate_normalized_discounted_cumulative_gain_at_p(p=100)
        self.calculate_normalized_discounted_cumulative_gain_at_p(p=1000)

class LivingLabsEvaluator(Evaluator):
    def __init__(self, task, eval_location):
        super().__init__(task, eval_location)
        try:
            base_url, api_key, run_id = eval_location.split('::')
        except ValueError:
            raise ArmyAntException("Must provide the base_url, api_key and run_id, separated by '::'")

        self.base_url = urljoin(base_url, 'api/v2/participant/')
        self.auth = HTTPBasicAuth(api_key, '')
        self.headers = { 'Content-Type': 'application/json' }

        requests_cache.install_cache('living_labs_cache', expire_after=10800)

        self.loop = asyncio.get_event_loop()
        self.index = Index.open(task.index_location, task.index_type, self.loop)

        self.run_id = run_id
        self.pickle_dir = '/opt/army-ant/cache/%s' % run_id
        if not os.path.exists(self.pickle_dir):
            os.mkdir(self.pickle_dir)

    def get_queries(self, qtype=None, qfilter=None):
        logging.info("Retrieving Living Labs queries")

        r = requests.get(urljoin(self.base_url, 'query'), headers=self.headers, auth=self.auth)
        if r.status_code != requests.codes.ok:
            r.raise_for_status()
        queries = r.json()['queries']
        
        if qtype: queries = list(filter(lambda q: q['type'] == qtype, queries))
        if qfilter: queries = list(filter(lambda q: q['qid'] in qfilter, queries))

        return queries

    def get_doclist_doc_ids(self, qid):
        logging.info("Retrieving Living Labs doclist for qid=%s" % qid)

        r = requests.get(urljoin(self.base_url, 'doclist/%s' % qid), headers=self.headers, auth=self.auth)
        if r.status_code != requests.codes.ok:
            r.raise_for_status()
        doc_ids = [doc['docid'] for doc in r.json()['doclist']]
        
        return set(doc_ids)

    def put_run(self, qid, runid, results):
        logging.info("Submitting Living Labs run for qid=%s and runid=%s" % (qid, runid))
        
        must_have_doc_ids = self.get_doclist_doc_ids(qid)

        # this first verification is required because an empty results variable is returned as a dictionary instead of a list
        if len(results) < 1:
            logging.warn("No results found, adding %d missing results with zero score" % len(must_have_doc_ids))
            results = [{'docID': doc_id} for doc_id in must_have_doc_ids]
        else:
            doc_ids = [result['docID'] for result in results]
            missing_doc_ids = must_have_doc_ids.difference(doc_ids)
            if len(missing_doc_ids) > 0:
                logging.warn("Adding %d missing results with zero score out of %d must have results" % (len(missing_doc_ids), len(must_have_doc_ids)))
                results.extend([{'docID': doc_id} for doc_id in missing_doc_ids])
        data = {
            'qid': qid,
            'runid': runid,
            'doclist': [{'docid': result['docID']} for result in results]
        }

        r = requests.put(urljoin(self.base_url, 'run/%s' % qid), data=json.dumps(data), headers=self.headers, auth=self.auth)
        if r.status_code == requests.codes.conflict:
            logger.warn("Run for qid=%s and runid=%s already exists, ignoring" % (qid, runid))
        else:
            r.raise_for_status()

    async def run(self):
        queries = self.get_queries()
        try:
            for query in queries:
                if self.interrupt:
                    logger.warn("Evaluation task was interrupted")
                    break

                logging.info("Searching for %s (qid=%s)" % (query['qstr'], query['qid']))

                pickle_path = os.path.join(self.pickle_dir, '%s.pickle' % query['qid'])
                if os.path.exists(pickle_path):
                    with open(pickle_path, 'rb') as f:
                        results = pickle.load(f)
                else:
                    engine_response = await self.index.search(query['qstr'], 0, 10000)
                    results = engine_response['results']
                    with open(pickle_path, 'wb') as f:
                        pickle.dump(results, f)

                logger.info("%d results found for %s (qid=%s)" % (len(results), query['qstr'], query['qid']))
                self.put_run(query['qid'], self.run_id, results)

            return EvaluationTaskStatus.SUBMITTED
        except HTTPError as e:
            logger.error(e)
            return EvaluationTaskStatus.ERROR

class EvaluationTaskStatus(IntEnum):
    WAITING = 1
    RUNNING = 2
    DONE = 3
    SUBMITTED = 4
    ERROR = 5

class EvaluationTask(object):
    def __init__(self, index_location, index_type, eval_format, topics_filename=None, topics_path=None,
                 assessments_filename=None, assessments_path=None, base_url=None, api_key=None, run_id=None,
                 status=EvaluationTaskStatus.WAITING, topics_md5=None, assessments_md5=None, time=None,
                 _id=None, results=None):
        self.index_location = index_location
        self.index_type = index_type
        self.eval_format = eval_format
        self.topics_filename = topics_filename
        self.topics_path = topics_path
        self.topics_md5 = topics_md5 or (md5(topics_path) if topics_path else None)
        self.assessments_filename = assessments_filename
        self.assessments_path = assessments_path
        self.assessments_md5 = assessments_md5 or (md5(assessments_path) if assessments_path else None)
        self.base_url = base_url
        self.api_key = api_key
        self.run_id = run_id
        self.status = EvaluationTaskStatus(status)
        self.time = time
        if results: self.results = results
        if _id: self._id = str(_id)

    def __repr__(self):
        return json.dumps(self.__dict__)

class EvaluationTaskManager(object):
    def __init__(self, db_location, default_eval_location):
        self.tasks = []
        self.running = None

        self.default_eval_location = default_eval_location
        self.results_dirname = os.path.join(default_eval_location, 'results')
        self.assessments_dirname = os.path.join(default_eval_location, 'assessments')
        self.spool_dirname = os.path.join(default_eval_location, 'spool')

        db_location_parts = db_location.split(':')
        
        if len(db_location_parts) > 1:
            db_location = db_location_parts[0]
            db_port = int(db_location_parts[1])
        else:
            db_port = 27017

        self.client = MongoClient(db_location, db_port)
        self.db = self.client['army_ant']

        self.db['evaluation_tasks'].create_index([
            ('topics_md5', pymongo.ASCENDING),
            ('assessments_md5', pymongo.ASCENDING),
            ('index_location', pymongo.ASCENDING),
            ('index_type', pymongo.ASCENDING)
        ], unique=True)

    def add_task(self, task):
        self.tasks.append(task)

    def del_task(self, task_id):
        return self.db['evaluation_tasks'].delete_one({ '_id': ObjectId(task_id) }).deleted_count > 0

    def reset_task(self, task_id):
        if self.running:
            self.running.interrupt = True
            if type(self.running) != LivingLabsEvaluator:
                self.running.remove_output()
        return self.db['evaluation_tasks'].update_one(
            { '_id': ObjectId(task_id) },
            { '$set': { 'status': 1 } }).matched_count > 0

    def get_tasks(self):
        tasks = []
        for task in self.db['evaluation_tasks'].find().sort('time'):
            tasks.append(EvaluationTask(**task))
        return tasks

    def get_waiting_task(self, task_id=None):
        query = { 'status': 1 }
        if task_id: query['_id'] = task_id

        task = self.db['evaluation_tasks'].find_one_and_update(
            query, { '$set': { 'status': 2 } },
            sort=[('time', pymongo.ASCENDING)])
        if task: return EvaluationTask(**task)

    def reset_running_tasks(self):
        logger.warning("Resetting running tasks to the WAITING status")
        self.db['evaluation_tasks'].update_many(
            { 'status': 2 },
            { '$set': { 'status': 1 } })
        if type(self.running) != LivingLabsEvaluator and self.running:
            self.running.remove_output()

    def queue(self):
        duplicate_error = False

        inserted_ids = []
        for task in self.tasks:
            try:
                task.time = int(round(time.time() * 1000))
                result = self.db['evaluation_tasks'].insert_one(task.__dict__)
                inserted_ids.append(result.inserted_id)
            except DuplicateKeyError as e:
                duplicate_error = True

        if duplicate_error:
            raise ArmyAntException("You can only launch one task per topics + assessments + engine.")
        
        return inserted_ids

    def save_results(self, task, results):
        self.db['evaluation_tasks'].update_one(
            { '_id': ObjectId(task._id) },
            { '$set': { 'status': EvaluationTaskStatus.DONE, 'results': results } })

    def set_status(self, task, status):
        self.db['evaluation_tasks'].update_one(
            { '_id': ObjectId(task._id) },
            { '$set': { 'status': status } })

    @contextmanager
    def get_results_archive(self, task_id):
        task = self.db['evaluation_tasks'].find_one({ '_id': ObjectId(task_id) })
        if task is None: return

        task = EvaluationTask(**task)
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_dir = os.path.join(tmp_dir, task_id)

            shutil.copytree(os.path.join(self.default_eval_location, 'assessments', task_id), out_dir)
            shutil.copytree(os.path.join(self.default_eval_location, 'results', task_id), os.path.join(out_dir, 'results'))

            with open(os.path.join(out_dir, "eval_metrics.csv"), 'w') as f:
                writer = csv.writer(f)
                writer.writerow(['metrics', 'value'])
                for metric, value in task.results.items():
                    writer.writerow([metric, value])

            archive_filename = os.path.join(tmp_dir, '%s.zip' % task_id)
            with zipfile.ZipFile(archive_filename, 'w') as zipf:
                zipdir(out_dir, zipf)

            yield archive_filename

    def get_results_json(self, task_id):
        task = self.db['evaluation_tasks'].find_one({ '_id': ObjectId(task_id) })
        if task is None: return

        task = EvaluationTask(**task)

        if task.eval_format == 'll-api':
            url = urljoin(task.base_url, 'api/v2/participant/outcome')
            auth = HTTPBasicAuth(task.api_key, '')
            headers = { 'Content-Type': 'application/json' }
            r = requests.get(url, headers=headers, auth=auth)
            return r.json()
            #return {
                #"outcomes": [
                    #{
                        #"impressions": 181, 
                        #"losses": 1, 
                        #"outcome": 0.5, 
                        #"qid": "all", 
                        #"site_id": "ssoar", 
                        #"test_period": {
                            #"end": "Sat, 15 Jul 2017 00:00:00 -0000", 
                            #"name": "TREC OpenSearch 2017 trial round", 
                            #"start": "Sat, 01 Jul 2017 00:00:00 -0000"
                        #}, 
                        #"ties": 179, 
                        #"type": "test", 
                        #"wins": 1
                    #}, 
                    #{
                        #"impressions": 59, 
                        #"losses": 13, 
                        #"outcome": 0.23529411764705882, 
                        #"qid": "all", 
                        #"site_id": "ssoar", 
                        #"test_period": None, 
                        #"ties": 42, 
                        #"type": "train", 
                        #"wins": 4
                    #}
                #]
            #}
        
        return {}

        HTTPBasicAuth
        return { 'base_url': task.base_url, 'api_key': task.api_key }

    def clean_spool(self):
        valid_spool_filenames = set([])
        for task in self.db['evaluation_tasks'].find():
            if task['eval_format'] == 'inex':
                valid_spool_filenames.add(os.path.basename(task['topics_path']))
                valid_spool_filenames.add(os.path.basename(task['assessments_path']))
        
        for filename in os.listdir(self.spool_dirname):
            path = os.path.join(self.spool_dirname, filename)
            if os.path.isfile(path) and not filename in valid_spool_filenames and (
                filename.startswith('eval_assessments_') or filename.startswith('eval_topics_')):
                logger.warning("Removing unreferenced spool file '%s'" % path)
                os.remove(path)

    def clean_results_and_assessments(self):
        valid_output_dirnames = set([])
        for task in self.db['evaluation_tasks'].find():
            valid_output_dirnames.add(os.path.basename(str(task['_id'])))
        
        for filename in os.listdir(self.results_dirname):
            path = os.path.join(self.results_dirname, filename)
            if not filename in valid_output_dirnames and len(filename) == 24: # 24 is the MongoDB ObjectId default length
                logger.warning("Removing unreferenced result directory '%s'" % path)
                shutil.rmtree(path)

        for filename in os.listdir(self.assessments_dirname):
            path = os.path.join(self.assessments_dirname, filename)
            if not filename in valid_output_dirnames and len(filename) == 24: # 24 is the MongoDB ObjectId default length
                logger.warning("Removing unreferenced assessments directory '%s'" % path)
                shutil.rmtree(path)

    async def process(self, task_id=None):
        try:
            self.clean_spool()
            self.clean_results_and_assessments()
            while True:
                task = self.get_waiting_task(task_id=task_id)
                if task:
                    try:
                        logger.info("Running evaluation task %s" % task._id)
                        if task.eval_format == 'll-api':
                            e = Evaluator.factory(task, '%s::%s::%s' % (task.base_url, task.api_key, task.run_id))
                        else:
                            e = Evaluator.factory(task, self.default_eval_location)

                        self.running = e
                        status = await e.run()

                        if task.eval_format == 'inex':
                            self.save_results(task, e.results)
                            self.running = None
                        elif task.eval_format == 'll-api':
                            self.set_status(task, status)

                    except ArmyAntException as e:
                        logger.error("Could not run evaluation task %s: %s" % (task._id, str(e)))

                if task_id: break
                await asyncio.sleep(5)
        except asyncio.CancelledError:
            self.reset_running_tasks()
