/* army-ant-gow-schema.groovy
 *
 * Helper functions for declaring JanusGraph schema elements
 * (vertex labels, edge labels, property keys) to accommodate
 * TP3 sample data.
 *
 * Sample usage in a gremlin.sh session:
 *
 * gremlin> :load data/army-ant-goe-schema.groovy
 * ==>true
 * ==>true
 * gremlin> t = JanusGraphFactory.open('conf/army-ant-cassandra-es-goe_*.properties')
 * ==>standardjanusgraph[cassandrathrift:[127.0.0.1]]
 * gremlin> defineGraphOfEntitySchema(t)
 * ==>null
 * gremlin> t.close()
 * ==>null
 * gremlin>
 */

def defineGraphOfEntitySchema(janusGraph) {
    janusGraph.tx().rollback()

    m = janusGraph.openManagement()
    
    // vertex labels
    term          = m.makeVertexLabel("term").make()
    entity        = m.makeVertexLabel("entity").make()
    
    // edge labels
    before        = m.makeEdgeLabel("before").make()
    containedIn   = m.makeEdgeLabel("contained_in").make()
    relatedTo     = m.makeEdgeLabel("related_to").make()
    
    // vertex and edge properties
    blid          = m.makePropertyKey("bulkLoader.vertex.id").dataType(Long.class).make()
    name          = m.makePropertyKey("name").dataType(String.class).make()
    url           = m.makePropertyKey("url").dataType(String.class).make()
    type          = m.makePropertyKey("type").dataType(String.class).make()
    docID         = m.makePropertyKey("doc_id").dataType(String.class).make()
    
    // global indices
    m.buildIndex("byBulkLoaderVertexId", Vertex.class).addKey(blid).buildCompositeIndex()
    m.buildIndex("byName", Vertex.class).addKey(name)buildCompositeIndex()
    m.buildIndex("byUrl", Vertex.class).addKey(url)buildCompositeIndex()
    m.buildIndex("byType", Vertex.class).addKey(type)buildCompositeIndex()
    m.buildIndex("byDocID", Edge.class).addKey(docID).buildCompositeIndex()
    
    // vertex centric indices
    //m.buildEdgeIndex(inWindowOf, "inWindowOfByDocID", Direction.BOTH, Order.decr, docID)
    m.commit()
}
