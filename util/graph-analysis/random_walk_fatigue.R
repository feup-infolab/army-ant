if (!require("pacman")) install.packages("pacman")

pacman::p_load(
  igraph
)

# -------------------------------------------------------------------------------------------------------------------#
#
# PageRank (Simulation)
#

page_rank_simulation <- function(g, d=0.85, steps=10000, PR = NULL) {
  for (i in 1:vcount(g)) {
    cat("==> Walking", steps, "random steps from node", i, "\n")
    PR <- page_rank_simulation_iter(g, i, d=d, steps=steps, PR = PR)
  }
  PR / norm(as.matrix(PR))
}

page_rank_simulation_iter <- function(g, start, d, steps, PR = NULL) {
  if (is.null(PR)) PR <- rep(0, vcount(g))

  teleport <- function() {
    sample(1:vcount(g), 1)
  }
  
  for (i in 1:steps) {
    if (runif(1) >= d) {
      # Teleport.
      start <- teleport()
    } else {
      # Choose a random outgoing vertex.
      out_v <- as.numeric(adjacent_vertices(g, start, mode = "out")[[1]])
      if (length(out_v) > 0) {
        start <- sample(out_v, 1)
      } else {
        # It's a sink. Teleport.
        start <- teleport()
      }
    }
    
    PR[start] <- PR[start] + 1
  }
  
  PR
}


# -------------------------------------------------------------------------------------------------------------------#
#
# PageRank (Power Iteration)
#

# This strategy is based on the fact that the primary eigenvector, corresponding to the highest eigenvalue,
# when multiplied by the original (stochatic) matrix, will result in the primary eigenvector again. Moreover,
# the primary eigenvalue of a Markov Matrix is always one.
page_rank_power_iteration <- function(g, d=0.85, eps=0.0001) {
  M <- as.matrix(as_adj(g))
  M <- scale(M, center=FALSE, scale=colSums(M))
  N <- vcount(g)
  v <- as.matrix(runif(N))
  v <- v / norm(v)
  last_v <- matrix(1, N) * 100
  M_hat <- d * M + (1 - d) / N * matrix(1, N, N)

  iter <- 0
  repeat {
    if (norm(v - last_v, "2") <= eps) break;
    last_v <- v
    v <- M_hat %*% v
    iter <- iter + 1
  }
  
  list(
    iterations=iter,
    vector=as.numeric(v)
  )
}



# -------------------------------------------------------------------------------------------------------------------#
#
# Fatigued PageRank (Simulation)
#

fatigued_transition_probability <- function(nf, method="zero", ...) {
  zero <- function() 0
  constant <- function(k=0.25) k
  exponential_decay <- function(k=0.25) 1 / (nf + k)
  eval(parse(text=sprintf("%s(...)", method)))
}

fatigued_page_rank_simulation <- function(g, d=0.85, steps=10000, PR = NULL, NF = NULL) {
  for (i in 1:vcount(g)) {
    cat("==> Walking", steps, "random steps from node", i, "\n")
    PR <- fatigued_page_rank_simulation_iter(g, i, d=d, steps=steps, PR = PR, NF = NF)
  }
  PR / norm(as.matrix(PR))
}

# Note: In RWS, there is no teleport, so the process would end when no outgoing vertices are available.
# This means that we cannot directly compare FPR with RWS.
fatigued_page_rank_simulation_iter <- function(g, start, d, steps, PR = NULL, NF = NULL) {
  if (is.null(PR)) PR <- rep(0, vcount(g))
  if (is.null(NF)) NF <- rep(0, vcount(g))
  
  teleport <- function() {
    non_fatigued <- which(NF != 0)
    if (length(non_fatigued) > 0) {
      sample(which(NF != 0), 1)
    } else {
      # Stay in current node.
      start
    }
  }
  
  for (i in 1:steps) {
    if (runif(1) >= d) {
      # Teleport to a non-fatigued node.
      start <- teleport()
    } else {
      # Choose a random non-fatigued outgoing vertex.
      out_v <- as.numeric(adjacent_vertices(g, start, mode = "out")[[1]])
      out_v <- out_v[which(NF[out_v] == 0)]
      if (length(out_v) > 0) {
        start <- sample(out_v, 1)
      } else {
        # It's a sink. Teleport to a non-fatigued node.
        start <- teleport()
      }
    }
    
    PR[start] <- PR[start] + 1
    NF[NF > 0] <- NF[NF > 0] - rep(1, length(NF[NF > 0]))
    NF[start] <- NF[start] + 1
  }
  
  PR
}


# -------------------------------------------------------------------------------------------------------------------#
#
# TESTS
#

#g <- make_graph("Zachary")
#V(g)$pr <- page_rank(g)$vector
#V(g)$pr_sim <- page_rank_simulation(g)
V(g)$fpr_sim <- fatigued_page_rank_simulation(g)
#cor(V(g)$pr, V(g)$pr_sim)


# -------------------------------------------------------------------------------------------------------------------#
#
# MAIN
#

#graph_path <- gzfile("/opt/army-ant/output/amazon-meta-simnet.gml.gz")
#g <- read.graph(graph_path, format = "gml")
#V(g)$pr <- page_rank(g, directed = TRUE)$vector
#V(g)$pr_sim <- page_rank_simulation(g)
#V(g)$fpr <- fatigued_page_rank(g)

# TODO Extract ranks before correlating? Nope. Spearman does this already!
#cor(V(g)$pr, V(g)$fpr, method = "spearman")

