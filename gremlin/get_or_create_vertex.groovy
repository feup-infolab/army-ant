get_or_create_vertex: {
  def it = g.V().has("name", vertex_name)
  if (it.hasNext()) {
    it.next()
  } else {
    vertex = g.addV().property("name", vertex_name)
    if (data != null) {
      data.each { k, v -> 
        vertex.property(k, v)
      }
    }
    vertex
  }
}
