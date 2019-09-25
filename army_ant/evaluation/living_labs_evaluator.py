import asyncio
import json
import logging
import os
import pickle
from urllib.parse import urljoin

import requests
import requests_cache
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError

from army_ant.evaluation import EvaluationTaskStatus, Evaluator
from army_ant.exception import ArmyAntException
from army_ant.index import Index

logger = logging.getLogger(__name__)


class LivingLabsEvaluator(Evaluator):
    def __init__(self, task, eval_location):
        super().__init__(task, eval_location)
        try:
            base_url, api_key, run_id = eval_location.split('::')
        except ValueError:
            raise ArmyAntException("Must provide the base_url, api_key and run_id, separated by '::'")

        self.base_url = urljoin(base_url, 'api/v2/participant/')
        self.auth = HTTPBasicAuth(api_key, '')
        self.headers = {'Content-Type': 'application/json'}

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

        if qtype:
            queries = list(filter(lambda q: q['type'] == qtype, queries))
        if qfilter:
            queries = list(filter(lambda q: q['qid'] in qfilter, queries))

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

        # This first verification is required because an empty results variable is returned as a dictionary
        # instead of a list.
        if len(results) < 1:
            logging.warn("No results found, adding %d missing results with zero score" % len(must_have_doc_ids))
            results = [{'docID': doc_id} for doc_id in must_have_doc_ids]
        else:
            doc_ids = [result['docID'] for result in results]
            missing_doc_ids = must_have_doc_ids.difference(doc_ids)
            if len(missing_doc_ids) > 0:
                logging.warn("Adding %d missing results with zero score out of %d must have results" % (
                    len(missing_doc_ids), len(must_have_doc_ids)))
                results.extend([{'docID': doc_id} for doc_id in missing_doc_ids])
        data = {
            'qid': qid,
            'runid': runid,
            'doclist': [{'docid': result['docID']} for result in results]
        }

        r = requests.put(urljoin(self.base_url, 'run/%s' % qid), data=json.dumps(data), headers=self.headers,
                         auth=self.auth)
        if r.status_code == requests.codes.conflict:
            logger.warning("Run for qid=%s and runid=%s already exists, ignoring" % (qid, runid))
        else:
            r.raise_for_status()

    async def run(self):
        queries = self.get_queries()
        try:
            for query in queries:
                if self.interrupt:
                    logger.warning("Evaluation task was interrupted")
                    break

                logging.info("Searching for %s (qid=%s)" % (query['qstr'], query['qid']))

                pickle_path = os.path.join(self.pickle_dir, '%s.pickle' % query['qid'])
                if os.path.exists(pickle_path):
                    with open(pickle_path, 'rb') as f:
                        results = pickle.load(f)
                else:
                    engine_response = await self.index.search(
                        query['qstr'], 0, 10000, task=Index.RetrievalTask.document_retrieval,
                        ranking_function=self.task.ranking_function, ranking_params=self.task.ranking_params)
                    results = engine_response['results']
                    with open(pickle_path, 'wb') as f:
                        pickle.dump(results, f)

                logger.info("%d results found for %s (qid=%s)" % (len(results), query['qstr'], query['qid']))
                self.put_run(query['qid'], self.run_id, results)

            return EvaluationTaskStatus.SUBMITTED
        except HTTPError as e:
            logger.error(e)
            return EvaluationTaskStatus.ERROR
