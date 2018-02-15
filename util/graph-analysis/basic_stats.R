library(igraph)
library(ggplot2)

basic_stats <- function(g) {
  data.frame(
    stat=c(
      "nodes",
      "edges",
      "diameter"
    ),
    value=c(
      vcount(g),
      ecount(g),
      diameter(g)
    )
  )
}

# Set this to your own GraphML file (it can optionally be gzip compressed)
graphml_path <- file('~/inex_2009_52t_nl-word2vec_simnet-reduced/word2vec_simnet.graphml.gz', encoding = 'utf-8')

g <- read.graph(graphml_path, format = "graphml")
c <- label.propagation.community(g)

stats <- basic_stats(g)