get_or_create_vertex: {
  def it;

  if (data != null && data.containsKey("type")) {
    it = g.V().has("name", vertexName).has("type", data["type"])
  } else {
    it = g.V().has("name", vertexName).hasNot("type")
  }

  if (it.hasNext()) {
    def vertex = it.next();
    if (data != null && data.containsKey("doc_id") && vertex.property("doc_id") == null) {
      vertex.property("doc_id", data["doc_id"])
    }
    vertex
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
