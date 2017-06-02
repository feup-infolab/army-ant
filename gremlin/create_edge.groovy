create_edge: {
  edge = g.V(sourceID).addE(edgeType).to(g.V(targetID))
  if (data != null) {
    data.each { k, v -> 
      edge.property(k, v)
    }
  }
  edge
}
