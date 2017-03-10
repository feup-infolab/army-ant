get_or_create_vertex: {
  def p = g.V().has("name", vertex_name)
  p.hasNext() ? p.next() : g.addV().property("name", vertex_name)
}
