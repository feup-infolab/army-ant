import asyncio
import csv
import logging
import os
import re
import time

from army_ant.evaluation import FilesystemEvaluator
from army_ant.exception import ArmyAntException
from army_ant.index import Index
from army_ant.util import ranking_params_to_params_id

logger = logging.getLogger(__name__)


class TRECEvaluator(FilesystemEvaluator):
    def __init__(self, task, eval_location):
        super().__init__(task, eval_location)

        self.loop = asyncio.get_event_loop()
        self.index = Index.open(self.task.index_location, self.task.index_type, self.loop)

    def get_topic_assessments(self):
        topic_doc_judgements = {}

        if not os.path.exists(self.task.assessments_path):
            raise ArmyAntException("Topic assessments file not found: %s" % self.task.assessments_path)

        with open(self.task.assessments_path, 'r') as f:
            for line in f:
                topic_id, _, id, judgement = line.split(' ')

                if topic_id not in topic_doc_judgements:
                    topic_doc_judgements[topic_id] = {}
                topic_doc_judgements[topic_id][id] = int(judgement)

        return topic_doc_judgements

    async def get_topic_results(self, ranking_params=None, topic_filter=None):
        topic_doc_judgements = self.get_topic_assessments()

        data = open(self.task.topics_path, 'r').read()

        topics = re.findall(
            r'<top>.*?<num>.*?Number:.*?(\d+).*?<title>.*?([^<]+).*?</top>',
            data, re.MULTILINE | re.DOTALL)

        topics = [(topic_id.strip(), query.strip()) for topic_id, query in topics]

        params_id = ranking_params_to_params_id(ranking_params)

        o_results_path = os.path.join(self.o_results_path, params_id)
        if not os.path.exists(o_results_path):
            os.makedirs(o_results_path)

        if params_id not in self.stats:
            self.stats[params_id] = {'ranking_params': ranking_params, 'query_time': {}}

        with open(os.path.join(o_results_path, '%s.res' % self.task.run_id), 'w') as trec_f:
            for topic_id, query in topics:
                if self.interrupt:
                    logger.warning("Evaluation task was interruped")
                    break

                if topic_filter and topic_id not in topic_filter:
                    logger.warning("Skipping topic '%s'" % topic_id)
                    continue

                logger.info("Obtaining results for query '%s' of topic '%s' using '%s' index at '%s'" % (
                    query, topic_id, self.task.index_type, self.task.index_location))
                start_time = time.time()
                engine_response = await self.index.search(
                    query, 0, 10000, task=Index.RetrievalTask.document_retrieval,
                    base_index_location=self.task.base_index_location, base_index_type=self.task.base_index_type,
                    ranking_function=self.task.ranking_function, ranking_params=ranking_params)
                end_time = int(round((time.time() - start_time) * 1000))
                self.stats[params_id]['query_time'][topic_id] = end_time

                with open(os.path.join(o_results_path, '%s.csv' % topic_id), 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['rank', 'score', 'doc_id', 'relevant'])
                    for i, result in zip(range(1, len(engine_response['results']) + 1), engine_response['results']):
                        doc_id = result['id']
                        score = result['score']
                        relevant = topic_doc_judgements[topic_id][doc_id] > 0 \
                            if doc_id in topic_doc_judgements[topic_id] else False
                        writer.writerow([i, score, doc_id, relevant])
                        trec_f.write("%s Q0 %s %s %s %s\n" % (topic_id, doc_id, i, score, self.task.run_id))

        self.stats[params_id]['total_query_time'] = sum([t for t in self.stats[params_id]['query_time'].values()])
        self.stats[params_id]['avg_query_time'] = (
            self.stats[params_id]['total_query_time'] / len(self.stats[params_id]['query_time']))
