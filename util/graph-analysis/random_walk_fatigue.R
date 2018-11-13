if (!require("pacman")) install.packages("pacman")

pacman::p_load(
  igraph
)

# -------------------------------------------------------------------------------------------------------------------#
#
# PageRank (Simulation)
#

page_rank_simulation <- function(g, d=0.85, steps=1000, PR = NULL) {
  for (i in 1:vcount(g)) {
    cat("==> Walking", steps, "random steps from node", i, "\n")
    PR <- page_rank_simulation_iter(g, i, d=d, steps=steps, PR = PR)
  }
  list(
    iterations=steps*vcount(g),
    vector=PR / norm(as.matrix(PR))
  )
}

page_rank_simulation_iter <- function(g, start, d, steps, PR = NULL) {
  if (is.null(PR)) PR <- rep(0, vcount(g))

  teleport <- function() {
    sample(1:vcount(g), 1)
  }
  
  PR[start] <- PR[start] + 1
  
  for (i in 1:steps) {
    if (runif(1) >= d) {
      # Teleport.
      start <- teleport()
    } else {
      # Choose a random outgoing vertex.
      out_v <- as.numeric(adjacent_vertices(g, start, mode = "out")[[1]])
      if (length(out_v) > 1) {
        start <- sample(out_v, 1)
      } else if (length(out_v) == 1) {
        # sample() won't work for vectors with a single value.
        start <- out_v
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
# when multiplied by the original (stochatic) matrix, will result in the primary eigenvector again, since
# the primary eigenvalue of a Markov (or stochastic) matrix is always one.
#
# $A v_1 = \lambda_1 v_1, \lambda_1 = 1 if is_stochastic(M)$
page_rank_power_iteration <- function(g, d=0.85, eps=0.0001) {
  # Columns must represent outgoing links
  M <- t(as.matrix(as_adj(g)))
  M <- scale(M, center=FALSE, scale=colSums(M))
  M[is.nan(M)] <- 0
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
    v <- v / norm(v)
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

fatigued_page_rank_simulation <- function(g, d=0.85, steps=1000, PR = NULL, NF = NULL) {
  for (i in 1:vcount(g)) {
    cat("==> Walking", steps, "random steps from node", i, "\n")
    PR <- fatigued_page_rank_simulation_iter(g, i, d=d, steps=steps, PR = PR, NF = NF)
  }
  
  list(
    iterations=steps * vcount(g),
    vector=PR / norm(as.matrix(PR))
  )
}

# Note: In RWS, there is no teleport, so the process would end when no outgoing vertices are available.
# This means that we cannot directly compare FPR with RWS.
fatigued_page_rank_simulation_iter <- function(g, start, d, steps, PR = NULL, NF = NULL) {
  if (is.null(PR)) PR <- rep(0, vcount(g))
  if (is.null(NF)) NF <- rep(0, vcount(g))
  
  teleport <- function() {
    non_fatigued <- which(NF != 0)
    if (length(non_fatigued) > 0) {
      sample(non_fatigued, 1)
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
      if (length(out_v) > 1) {
        start <- sample(out_v, 1)
      } else if (length(out_v) == 1) {
        # sample() won't work for vectors with a single value.
        start <- out_v
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
# Fatigued PageRank (Power Iteration)
#

fatigued_page_rank_power_iteration <- function(g, d=0.85, eps=0.0001) {
  # Columns must represent outgoing links
  M <- t(as.matrix(as_adj(g)))
  M <- scale(M, center=FALSE, scale=colSums(M))
  M[is.nan(M)] <- 0
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
    v <- v / norm(v)
    iter <- iter + 1
  }
  
  list(
    iterations=iter,
    vector=as.numeric(v)
  )
}


# -------------------------------------------------------------------------------------------------------------------#
#
# TESTS
#

#g <- make_graph("Zachary")
g <- make_graph(c(1,2, 2,3, 3,2, 4,2, 4,3, 3,1, 4,5, 5,3, 3,6, 6,7, 7,8, 8,1, 8,3))

V(g)$pr <- page_rank(g)$vector

pr_sim <- page_rank_simulation(g)
V(g)$pr_sim <- pr_sim$vector
V(g)$pr_sim_iter <- pr_sim$iterations

pr_iter <- page_rank_power_iteration(g)
V(g)$pr_iter <- pr_iter$vector
V(g)$pr_iter_iter <- pr_iter$iterations

fpr_sim <- fatigued_page_rank_simulation(g)
V(g)$fpr_sim <- fpr_sim$vector
V(g)$fpr_sim_iter <- fpr_sim$iterations

cor(V(g)$pr, V(g)$pr_sim, method="pearson")
cor(V(g)$pr, V(g)$pr_sim, method="spearman")
cor(V(g)$pr, V(g)$pr_iter, method="pearson")
cor(V(g)$pr, V(g)$pr_iter, method="spearman")
cor(V(g)$pr, V(g)$fpr_sim, method="pearson")
cor(V(g)$pr, V(g)$fpr_sim, method="spearman")


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

