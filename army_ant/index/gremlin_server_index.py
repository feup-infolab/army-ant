#!/usr/bin/env python
#
# gremlin_server_index.py
# José Devezas (joseluisdevezas@gmail.com)
# 2018-03-09 (refactor: 2019-03-14)

import logging

from army_ant.index import ServiceIndex
from army_ant.util import load_gremlin_script

logger = logging.getLogger(__name__)


class GremlinServerIndex(ServiceIndex):
    def __init__(self, reader, index_location, loop):
        super().__init__(reader, index_location, loop)
        self.graph = self.index_path if self.index_path else 'graph'
        self.client = None

    async def get_or_create_vertex(self, vertex_name, data=None):
        result_set = await self.client.submit(
            ('g = %s.traversal()\n' % self.graph)
            + load_gremlin_script('get_or_create_vertex'),
            {'vertexName': vertex_name, 'data': data})
        results = await result_set.all()
        return results[0] if len(results) > 0 else None

    async def get_or_create_edge(self, source_vertex, target_vertex, edge_type='before', data=None):
        result_set = await self.client.submit(
            ('g = %s.traversal()\n' % self.graph)
            + load_gremlin_script('get_or_create_edge'), {
                'sourceID': source_vertex.id,
                'targetID': target_vertex.id,
                'edgeType': edge_type,
                'data': data
            })
        results = await result_set.all()
        return results[0] if len(results) > 0 else None

    async def to_edge_list(self, use_names=False):
        result_set = await self.client.submit(
            ('g = %s.traversal()\n' % self.graph)
            + load_gremlin_script('convert_to_edge_list'), {
                'useNames': use_names
            })
        async for edge in result_set:
            yield edge
