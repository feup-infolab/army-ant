get_or_create_edge: {
  def it;
  
  if (data != null && data.containsKey("doc_id")) {
    it = g.V(sourceID).outE().has("doc_id", data["doc_id"]).inV().hasId(targetID)
  } else {
    it = g.V(sourceID).outE().inV().hasId(targetID)
  }

  if (it.hasNext()) {
    it.next()
  } else {
    edge = g.V(sourceID).addE(edgeType).to(g.V(targetID))
    if (data != null) {
      data.each { k, v -> 
        edge.property(k, v)
      }
    }
    edge
  }
}
