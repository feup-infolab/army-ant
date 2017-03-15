get_or_create_vertex: {
  def it = g.V().has("name", vertexName)
  if (it.hasNext()) {
    it.next()
  } else {
    vertex = g.addV().property("name", vertexName)
    if (data != null) {
      data.each { k, v -> 
        vertex.property(k, v)
      }
    }
    vertex
  }
}
