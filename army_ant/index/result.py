#!/usr/bin/env python
#
# result.py
# José Devezas (joseluisdevezas@gmail.com)
# 2018-03-09 (refactor: 2019-03-14)

import logging

logger = logging.getLogger(__name__)


class Result(object):
    def __init__(self, score, id, name, type=None, components=None):
        self.id = id
        self.name = name
        self.type = type
        self.score = score
        self.components = components

    def set_component(self, key, value):
        if self.components is None:
            self.components = []
        self.components[key] = value

    def unset_component(self, key):
        del self.components[key]
        if len(self.components) == 0:
            self.components = None

    def __getitem__(self, key):
        if key == 'id':
            return self.id
        elif key == 'name':
            return self.name
        elif key == 'type':
            return self.type
        elif key == 'score':
            return self.score
        else:
            raise KeyError(key)

    def __contains__(self, key):
        return (key == 'id' and self.id or
                key == 'name' and self.name or
                key == 'type' and self.type or
                key == 'score' and self.score)

    def __repr__(self):
        return """{ "score": %f, "id": %s, "name": %s, "type": %s, "has_components": %s }""" % (
            self.score, self.id, self.name, self.type, ("true" if self.components else "false"))
