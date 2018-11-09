if (!require("pacman")) install.packages("pacman")

pacman::p_load(
  igraph
)

fatigued_page_rank <- function(g) {
  0 # TODO
}

graph_path <- gzfile("/opt/army-ant/output/amazon-meta-simnet.gml.gz")
g <- read.graph(graph_path, format = "gml")
V(g)$page_rank <- page_rank(g, directed = FALSE)$vector
V(g)$fatigued_page_rank <- fatigued_page_rank(g)

# TODO Extract ranks before correlating?
cor(V(g)$page_rank, V(g)$fatigued_page_rank, method = "spearman")