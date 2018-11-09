if (!require("pacman")) install.packages("pacman")

pacman::p_load(
  igraph
)

graph_path <- gzfile("/opt/army-ant/output/amazon-meta-simnet.gml.gz")
g <- read.graph(graph_path, format = "gml")
V(g)$page_rank <- page_rank(g, directed = FALSE)$vector