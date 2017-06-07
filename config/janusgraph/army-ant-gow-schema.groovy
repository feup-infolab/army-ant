/* army-ant-gow-schema.groovy
 *
 * Helper functions for declaring JanusGraph schema elements
 * (vertex labels, edge labels, property keys) to accommodate
 * TP3 sample data.
 *
 * Sample usage in a gremlin.sh session:
 *
 * gremlin> :load data/army-ant-gow-schema.groovy
 * ==>true
 * ==>true
 * gremlin> t = JanusGraphFactory.open('conf/army-ant-cassandra-es-gow_*.properties')
 * ==>standardjanusgraph[cassandrathrift:[127.0.0.1]]
 * gremlin> defineGraphOfWordSchema(t)
 * ==>null
 * gremlin> t.close()
 * ==>null
 * gremlin>
 */

def defineGraphOfWordSchema(janusGraph) {
    janusGraph.tx().rollback()

    m = janusGraph.openManagement()
    
    // vertex labels
    term          = m.makeVertexLabel("term").make()
    
    // edge labels
    inWindowOf    = m.makeEdgeLabel("in_window_of").make()
    
    // vertex and edge properties
    blid          = m.makePropertyKey("bulkLoader.vertex.id").dataType(Long.class).make()
    name          = m.makePropertyKey("name").dataType(String.class).make()
    docID         = m.makePropertyKey("doc_id").dataType(String.class).make()
    
    // global indices
    m.buildIndex("byBulkLoaderVertexId", Vertex.class).addKey(blid).buildCompositeIndex()
    m.buildIndex("byName", Vertex.class).addKey(name)buildCompositeIndex()
    m.buildIndex("byDocID", Edge.class).addKey(docID).buildCompositeIndex()
    
    // vertex centric indices
    //m.buildEdgeIndex(inWindowOf, "inWindowOfByDocID", Direction.BOTH, Order.decr, docID)
    m.commit()
}
