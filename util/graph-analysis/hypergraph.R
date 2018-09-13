if (!require("pacman")) install.packages("pacman")

pacman::p_load(
  "dplyr",
  "tidyr"
)

random_walk <- function(hypergraph, source_node_id, l, r, visited_nodes=list(), visited_hyperedges=list()) {
  if (r == 0) {
    return(list(nodes=visited_nodes, hyperedges=visited_hyperedges))
  }
  
  random_node_id <- source_node_id
  visited_nodes[[random_node_id]] <- ifelse(
    is.null(visited_nodes[[random_node_id]]), 1, visited_nodes[[random_node_id]] + 1)
  
  for (i in 1:l) {
    random_hyperedge_id <- sample(hypergraph$nodes[[random_node_id]]$hyperedges, 1)
    random_node_id <- sample(hypergraph$hyperedges[[random_hyperedge_id]]$nodes, 1)
    
    visited_nodes[[random_node_id]] <- ifelse(
      is.null(visited_nodes[[random_node_id]]), 1, visited_nodes[[random_node_id]] + 1)
    
    visited_hyperedges[[random_hyperedge_id]] <- ifelse(
      is.null(visited_hyperedges[[random_hyperedge_id]]), 1, visited_hyperedges[[random_hyperedge_id]] + 1)
  }
  
  random_walk(hypergraph, source_node_id, l, r-1, visited_nodes, visited_hyperedges)
}

merge_random_walks <- function(..., normalize=T, rank=T) {
  nodes <- lapply(list(...), function(rw) rw$nodes) %>%
    bind_rows() %>%
    summarise_all(funs(sum(., na.rm = T))) %>%
    unlist()
  
  hyperedges <- lapply(list(...), function(rw) rw$hyperedges) %>%
    bind_rows() %>%
    summarise_all(funs(sum(., na.rm = T))) %>%
    unlist()

  if (normalize) {
    nodes <- nodes / max(nodes)
    hyperedges <- hyperedges / max(hyperedges)
  }
  
  if (rank) {
    nodes <- sort(nodes, decreasing = T)
    hyperedges <- sort(hyperedges, decreasing = T)
  }

  list(
    nodes=nodes,
    hyperdges=hyperedges
  )
}

hg <- list(
  nodes=list(
    n1=list(hyperedges=c("d1")),
    n2=list(hyperedges=c("d1", "d2")),
    n3=list(hyperedges=c("d2")),
    n4=list(hyperedges=c("d1")),
    n5=list(hyperedges=c("d1", "d2", "d3")),
    n6=list(hyperedges=c("d2", "d3"))
  ),
  hyperedges=list(
    d1=list(nodes=c("n1", "n2", "n4", "n5")),
    d2=list(nodes=c("n2", "n3", "n5", "n6")),
    d3=list(nodes=c("n5", "n6"))
  )
)

l <- 2
r <- 10

rw <- list(
  random_walk(hg, "n5", l, r),
  random_walk(hg, "n6", l, r),
  normalize=F
)

do.call(merge_random_walks, rw)