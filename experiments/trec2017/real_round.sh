# Written using test.py (test_livinglabsevaluator). Not ready for reproducibility. Must create evaluator CLI runner.
cd ../.. && \
  time ./test.py localhost:8182/gow_trec2017 gow_csv 6E6B10EB18D56CAE-4WHODA8IRV121MNV gow_trec2017-real_round && \
  time ./test.py localhost:8182/goe_trec2017 goe_csv 6E6B10EB18D56CAE-4WHODA8IRV121MNV goe_trec2017-real_round
