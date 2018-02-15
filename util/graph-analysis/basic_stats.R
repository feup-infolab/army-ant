library(igraph)

graphml_path <- file('~/inex_2009_52t_nl-word2vec_simnet-reduced/word2vec_simnet.graphml.gz', encoding = 'utf-8')
g <- read.graph(graphml_path, format = "graphml")