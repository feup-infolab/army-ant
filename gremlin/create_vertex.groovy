create_vertex: {
  vertex = g.addV().property("name", vertexName)
  if (data != null) {
    data.each { k, v -> 
      vertex.property(k, v)
    }
  }
  vertex
}
