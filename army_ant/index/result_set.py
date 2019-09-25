#!/usr/bin/env python
#
# result_set.py
# José Devezas (joseluisdevezas@gmail.com)
# 2018-03-09 (refactor: 2019-03-14)

import logging

logger = logging.getLogger(__name__)


class ResultSet(object):
    def __init__(self, results, num_docs, trace=None, trace_ascii=None):
        self.results = results
        self.num_docs = num_docs
        self.trace = trace
        self.trace_ascii = trace_ascii

    def __len__(self):
        return len(self.results)

    def __iter__(self):
        self.iter = iter(self.results)
        return self.iter

    def __next__(self):
        return next(self.iter)

    # For compatibility with external implementations depending on dictionaries
    def __getitem__(self, key):
        if key == 'results':
            return self.results
        elif key == 'numDocs':
            return self.num_docs
        elif key == 'trace':
            return self.trace
        elif key == 'traceASCII':
            return self.trace_ascii
        else:
            raise KeyError

    def __contains__(self, key):
        return (key == 'results' and self.results or
                key == 'numDocs' and self.num_docs or
                key == 'trace' and self.trace or
                key == 'traceASCII' and self.trace_ascii)

    def __repr__(self):
        return "[ %s ]" % ', '.join([str(result) for result in self.results])
