import csv
import itertools
import logging
import math
import os
import shutil
from collections import OrderedDict

import pandas as pd

from army_ant.evaluation import Evaluator
from army_ant.exception import ArmyAntException
from army_ant.util import ranking_params_to_params_id, safe_div
from army_ant.util.stats import gmean

logger = logging.getLogger(__name__)

pd.set_option("display.max_rows", 10)


#
# TODO REQUIRES MASSIVE REFACTORING!
#
# Evaluation metrics should be calculated in separate functions and reused by all evaluators.
#
# Note: we have already centralized most of the calculations in FilesystemEvaluator, but we
# should separate calculations from reading methods.
#

def dcg(rel, p):
    return sum(rel[i-1] / math.log2(i + 1) for i in range(1, min(len(rel), p) + 1))


class FilesystemEvaluator(Evaluator):
    def __init__(self, task, eval_location):
        super().__init__(task, eval_location)

        self.o_results_path = os.path.join(eval_location, 'results', task._id)
        self.o_assessments_path = os.path.join(eval_location, 'assessments', task._id)

        try:
            os.makedirs(self.o_results_path)
        except FileExistsError:
            raise ArmyAntException("Results directory '%s' already exists" % self.o_results_path)

        try:
            os.makedirs(self.o_assessments_path)
        except FileExistsError:
            raise ArmyAntException("Assessments directory '%s' already exists" % self.o_assessments_path)

    def remove_output(self):
        shutil.rmtree(self.o_results_path, ignore_errors=True)
        shutil.rmtree(self.o_assessments_path, ignore_errors=True)

    def path_to_topic_id(self, path):
        return os.path.basename(os.path.splitext(path)[0])

    def get_result_files(self, params_id):
        o_results_path = os.path.join(self.o_results_path, params_id)
        return [
            os.path.join(o_results_path, f)
            for f in os.listdir(o_results_path)
            if f.endswith('.csv') and os.path.isfile(os.path.join(o_results_path, f))]

    def f_score(self, precision, recall, beta=1):
        if precision == 0 and recall == 0:
            return 0
        return safe_div((1 + beta ** 2) * (precision * recall), (beta ** 2 * precision) + recall)

    def calculate_precision_recall(self, ranking_params=None):
        # topic_id -> doc_id -> num_relevant_chars
        topic_doc_judgements = self.get_topic_assessments()

        params_id = ranking_params_to_params_id(ranking_params)
        result_files = self.get_result_files(params_id)

        o_eval_details_dir = os.path.join(self.o_assessments_path, params_id)
        if not os.path.exists(o_eval_details_dir):
            os.makedirs(o_eval_details_dir)
        o_eval_details_file = os.path.join(o_eval_details_dir, 'precision_recall_per_topic.csv')

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

                    # Positives, i.e., documents in the list of results.
                    for doc_id in result_doc_ids:
                        relevant = topic_doc_judgements.get(topic_id, {}).get(doc_id, 0) > 0
                        if relevant:
                            tp += 1
                        else:
                            fp += 1

                    # Negatives are unknown, because they refer to documents in the qrels that weren't returned.
                    for doc_id, judgment in topic_doc_judgements.get(topic_id, {}).items():
                        # Skip positives
                        if doc_id not in result_doc_ids:
                            relevant = judgment > 0
                            if relevant:
                                fn += 1
                            else:
                                tn += 1

                    # print(topic_id, "num_ret =", tp+fp, "num_rel =", tp+fn, "num_rel_ret =", tp)

                    tps.append(tp)
                    fps.append(fp)
                    tns.append(tn)
                    fns.append(fn)

                    logger.debug(
                        "%s - TP(%d) + FP(%d) + TN(%d) + FN(%d) = %d" % (topic_id, tp, fp, tn, fn, tp + fp + tn + fn))

                    precision = safe_div(tp, tp + fp)
                    precisions.append(precision)

                    recall = safe_div(tp, tp + fn)
                    recalls.append(recall)

                    f_0_5_score = self.f_score(precision, recall, beta=0.5)
                    f_0_5_scores.append(f_0_5_score)

                    f_1_score = self.f_score(precision, recall, beta=1)
                    f_1_scores.append(f_1_score)

                    f_2_score = self.f_score(precision, recall, beta=2)
                    f_2_scores.append(f_2_score)

                    writer.writerow([topic_id, tp, fp, tn, fn, precision, recall, f_0_5_score, f_1_score, f_2_score])

            if params_id not in self.results:
                self.results[params_id] = {'ranking_params': ranking_params, 'metrics': {}}
            self.results[params_id]['metrics']['Micro Avg Prec'] = safe_div(sum(tps), sum(tps) + sum(fps))
            self.results[params_id]['metrics']['Micro Avg Rec'] = safe_div(sum(tps), sum(tps) + sum(fns))
            self.results[params_id]['metrics']['Macro Avg Prec'] = safe_div(sum(precisions), len(precisions))
            self.results[params_id]['metrics']['Macro Avg Rec'] = safe_div(sum(recalls), len(recalls))

            self.results[params_id]['metrics']['Micro Avg F0_5'] = self.f_score(
                self.results[params_id]['metrics']['Micro Avg Prec'],
                self.results[params_id]['metrics']['Micro Avg Rec'], beta=0.5)
            self.results[params_id]['metrics']['Micro Avg F1'] = self.f_score(
                self.results[params_id]['metrics']['Micro Avg Prec'],
                self.results[params_id]['metrics']['Micro Avg Rec'], beta=1)
            self.results[params_id]['metrics']['Micro Avg F2'] = self.f_score(
                self.results[params_id]['metrics']['Micro Avg Prec'],
                self.results[params_id]['metrics']['Micro Avg Rec'], beta=2)

            self.results[params_id]['metrics']['Macro Avg F0_5'] = self.f_score(
                self.results[params_id]['metrics']['Macro Avg Prec'],
                self.results[params_id]['metrics']['Macro Avg Rec'], beta=0.5)
            self.results[params_id]['metrics']['Macro Avg F1'] = self.f_score(
                self.results[params_id]['metrics']['Macro Avg Prec'],
                self.results[params_id]['metrics']['Macro Avg Rec'], beta=1)
            self.results[params_id]['metrics']['Macro Avg F2'] = self.f_score(
                self.results[params_id]['metrics']['Macro Avg Prec'],
                self.results[params_id]['metrics']['Macro Avg Rec'], beta=2)

            # Same as TREC set_F.0.25 (beta^2 = 0.25 <=> 0.5^2 = 0.25), set_F.1 and set_F.4 (beta^2 = 4 <=> 2^2 = 4)
            self.results[params_id]['metrics']['F0_5'] = safe_div(sum(f_0_5_scores), len(f_0_5_scores))
            self.results[params_id]['metrics']['F1'] = safe_div(sum(f_1_scores), len(f_1_scores))
            self.results[params_id]['metrics']['F2'] = safe_div(sum(f_2_scores), len(f_2_scores))

    def calculate_precision_at_n(self, n=10, ranking_params=None):
        params_id = ranking_params_to_params_id(ranking_params)
        result_files = self.get_result_files(params_id)

        o_eval_details_dir = os.path.join(self.o_assessments_path, params_id)
        if not os.path.exists(o_eval_details_dir):
            os.makedirs(o_eval_details_dir)
        o_eval_details_file = os.path.join(o_eval_details_dir, 'p_at_%d-precision_at_%d_per_topic.csv' % (n, n))

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

            if params_id not in self.results:
                self.results[params_id] = {'ranking_params': ranking_params, 'metrics': {}}
            self.results[params_id]['metrics']['P@%d' % n] = safe_div(sum(precisions_at_n), len(precisions_at_n))

    def calculate_mean_average_precision(self, ranking_params=None):
        topic_doc_judgements = self.get_topic_assessments()
        params_id = ranking_params_to_params_id(ranking_params)
        result_files = self.get_result_files(params_id)

        o_eval_details_dir = os.path.join(self.o_assessments_path, params_id)
        if not os.path.exists(o_eval_details_dir):
            os.makedirs(o_eval_details_dir)
        o_eval_details_file = os.path.join(o_eval_details_dir, 'map_average_precision_per_topic.csv')

        with open(o_eval_details_file, 'w') as ef:
            writer = csv.writer(ef)
            writer.writerow(['topic_id', 'avg_precision'])

            num_rel_per_topic = {}
            for topic_id, judgements in topic_doc_judgements.items():
                num_rel_per_topic[topic_id] = 0
                for doc_id, rel in judgements.items():
                    if rel > 0:
                        num_rel_per_topic[topic_id] += 1

            avg_precisions = []
            for result_file in result_files:
                topic_id = self.path_to_topic_id(result_file)

                precisions = []
                with open(result_file, 'r') as rf:
                    reader = csv.DictReader(rf)
                    results = []
                    for row in reader:
                        results.append(row['relevant'] == 'True')

                    for i in range(1, len(results) + 1):
                        rel = results[0:i]
                        if not rel[i-1]:
                            continue
                        p = safe_div(sum(rel), len(rel))
                        precisions.append(p)

                    avg_precision = safe_div(sum(precisions), num_rel_per_topic[topic_id])
                    avg_precisions.append(avg_precision)
                    writer.writerow([topic_id, avg_precision])

            if params_id not in self.results:
                self.results[params_id] = {'ranking_params': ranking_params, 'metrics': {}}
            self.results[params_id]['metrics']['MAP'] = safe_div(sum(avg_precisions), len(avg_precisions))
            # This is an approximation of np.prod(avg_precision)**(1/len(avg_precision)) that works with zero values.
            self.results[params_id]['metrics']['GMAP'] = gmean(avg_precisions)

    def calculate_normalized_discounted_cumulative_gain_at_p(self, p=10, ranking_params=None):
        topic_doc_judgements = self.get_topic_assessments()
        params_id = ranking_params_to_params_id(ranking_params)
        result_files = self.get_result_files(params_id)

        ideal_rankings = {}
        qrels = {}
        for topic_id, judgements in topic_doc_judgements.items():
            ideal_rankings[topic_id] = sorted((judgement for judgement in judgements.values()), reverse=True)

            qrels[topic_id] = {'doc_id': [], 'rel': []}
            for doc_id, rel in judgements.items():
                qrels[topic_id]['doc_id'].append(doc_id)
                qrels[topic_id]['rel'].append(rel)
            qrels[topic_id] = pd.DataFrame(qrels[topic_id], columns=['doc_id', 'rel'])

        ndcgs = []
        for result_file in result_files:
            topic_id = self.path_to_topic_id(result_file)

            df = pd.read_csv(result_file, converters={'doc_id': lambda d: str(d)})
            df = df.merge(qrels[topic_id], on='doc_id', how='left')
            df.rel.fillna(value=0, inplace=True)

            dcg_p = dcg(df.rel, p)
            idcg_p = dcg(ideal_rankings[topic_id], p)
            ndcgs.append(safe_div(dcg_p, idcg_p))

        if params_id not in self.results:
            self.results[params_id] = {'ranking_params': ranking_params, 'metrics': {}}
        self.results[params_id]['metrics']['NDCG@%d' % p] = safe_div(sum(ndcgs), len(ndcgs))

    async def run_with_params(self, ranking_params=None):
        await self.get_topic_results(ranking_params=ranking_params)

        self.calculate_precision_recall(ranking_params=ranking_params)

        self.calculate_precision_at_n(n=10, ranking_params=ranking_params)
        self.calculate_precision_at_n(n=100, ranking_params=ranking_params)
        self.calculate_precision_at_n(n=1000, ranking_params=ranking_params)

        self.calculate_mean_average_precision(ranking_params=ranking_params)

        self.calculate_normalized_discounted_cumulative_gain_at_p(p=10, ranking_params=ranking_params)
        self.calculate_normalized_discounted_cumulative_gain_at_p(p=100, ranking_params=ranking_params)
        self.calculate_normalized_discounted_cumulative_gain_at_p(p=1000, ranking_params=ranking_params)

    async def run(self):
        if self.task.ranking_params:
            sorted_ranking_params = OrderedDict(sorted(self.task.ranking_params.items(), key=lambda d: d[0]))
            keys = list(sorted_ranking_params.keys())
            values = list(sorted_ranking_params.values())

            for param_values in itertools.product(*values):
                ranking_params = dict(zip(keys, param_values))
                await self.run_with_params(ranking_params)
        else:
            await self.run_with_params()
