import logging

from datetime import datetime

from army_ant.index import Index
from army_ant.exception import ArmyAntException


logger = logging.getLogger(__name__)


class Evaluator(object):
    @staticmethod
    def factory(task, eval_location):
        import army_ant.evaluation as evl

        if task.eval_format == 'inex':
            return evl.INEXEvaluator(task, eval_location, Index.RetrievalTask.document_retrieval)
        if task.eval_format == 'inex-xer':
            return evl.INEXEvaluator(task, eval_location, Index.RetrievalTask.entity_retrieval)
        if task.eval_format == 'trec':
            return evl.TRECEvaluator(task, eval_location)
        elif task.eval_format == 'll-api':
            return evl.LivingLabsEvaluator(task, eval_location)
        else:
            raise ArmyAntException("Unsupported evaluator format")

    def __init__(self, task, eval_location):
        self.task = task
        self.results = {}
        self.stats = {}
        self.interrupt = False
        self.start_date = datetime.now()

    async def run(self):
        raise ArmyAntException("Unsupported evaluator format %s" % self.task.eval_format)
