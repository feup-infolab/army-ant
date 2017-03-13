get_or_create_edge: {
  def it = g.V(source_id).out().hasId(target_id)
  if (it.hasNext()) {
    it.next()
  } else {
    edge = g.V(source_id).addE(edge_type).to(g.V(target_id))
    if (data != null) {
      data.each { k, v -> 
        edge.property(k, v)
      }
    }
    edge
  }
}
