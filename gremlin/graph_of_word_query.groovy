graph_of_word_query: {
  g.V().project("v","degree").by().by(inE().count())
}
