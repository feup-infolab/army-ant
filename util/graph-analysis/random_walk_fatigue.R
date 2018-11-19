if (!require("pacman")) install.packages("pacman")

pacman::p_load(
  igraph
)

options(stringsAsFactors=FALSE)
options(scipen=50)

# -------------------------------------------------------------------------------------------------------------------#
#
# PageRank (Simulation)
#

page_rank_simulation <- function(g, d=0.85, steps=10000, PR = NULL) {
  for (i in 1:vcount(g)) {
    cat("==> Walking", steps, "random steps from node", i, "with teleport\n")
    PR <- page_rank_simulation_iter(g, start=i, d=d, steps=steps, PR = PR)
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
  M_hat <- d * M + (1-d)/N * matrix(1, N, N)

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

fatigued_page_rank_simulation <- function(g, d=0.85, nf=10, steps=1000, use_teleport=FALSE, FPR = NULL) {
  for (i in 1:vcount(g)) {
    teleport_str <- ifelse(use_teleport, "teleport", "without teleport")
    cat("==> Walking", steps, "random steps from node", i, "with fatigue and", teleport_str, "\n")
    FPR <- fatigued_page_rank_simulation_iter(g, i, d=d, nf=nf, steps=steps, use_teleport = use_teleport, FPR = FPR)
  }

  FPR$vector <- FPR$vector / norm(as.matrix(FPR$vector))
  
  FPR
}

# Note: In RWS, there is no teleport, so the process would end when no outgoing vertices are available.
# This means that we cannot directly compare FPR with RWS.
fatigued_page_rank_simulation_iter <- function(g, start, d, nf, steps, use_teleport=FALSE, FPR = NULL) {
  if (is.null(FPR)) FPR <- list(vector=rep(0, vcount(g)), NF=rep(0, vcount(g)), iterations=0)

  teleport <- function() {
    non_fatigued <- which(FPR$NF == 0)
    if (length(non_fatigued) > 0) {
      sample(non_fatigued, 1)
    } else {
      # Stay in current node.
      start
    }
  }
  
  for (i in 1:steps) {
    if (use_teleport) {
      # WITH TELEPORT

      if (runif(1) >= d) {
        # Teleport to a non-fatigued node.
        start <- teleport()
      } else {
        # Choose a random non-fatigued outgoing vertex.
        out_v <- as.numeric(adjacent_vertices(g, start, mode = "out")[[1]])
        out_v <- out_v[which(FPR$NF[out_v] == 0)]
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
    } else {
      # WITHOUT TELEPORT

      # Choose a random non-fatigued outgoing vertex.
      out_v <- as.numeric(adjacent_vertices(g, start, mode = "out")[[1]])
      out_v <- out_v[which(FPR$NF[out_v] == 0)]
      if (length(out_v) > 1) {
        start <- sample(out_v, 1)
      } else if (length(out_v) == 1) {
        # sample() won't work for vectors with a single value.
        start <- out_v
      } else {
        # It's a sink. Finish.
        break
      }
    }

    FPR$vector[start] <- FPR$vector[start] + 1
    FPR$NF[FPR$NF > 0] <- FPR$NF[FPR$NF > 0] - rep(1, length(FPR$NF[FPR$NF > 0]))
    FPR$NF[start] <- nf
    FPR$iterations <- FPR$iterations + 1
  }
  
  FPR
}


# -------------------------------------------------------------------------------------------------------------------#
#
# Fatigued PageRank (Power Iteration)
#

# For now, nf is ignored. There is instead a probability of a node being fatigued, depending on its in-degree.
# This must be revised to also depend on the number of cycles of node fatigue (nf).
fatigued_page_rank_power_iteration <- function(g, d=0.85, nf=10, eps=0.0001, fatigue_method='3ord', ...) {
  stopifnot(fatigue_method %in% c("1ord", "2ord", "3ord"))

  first_order_fatigue <- function(M, ...) {
    kwargs <- list(...)
    lambda <- ifelse("lambda" %in% kwargs, kwargs$lambda, 0.85)
    teleport <- ifelse(is.null(kwargs$teleport), FALSE, kwargs$teleport)
    N <- nrow(M)

    P_i <- rowSums(M)
    P_i <- 1 - 1 / (P_i + 1)
    P_i <- matrix(rep(P_i, length(P_i)), length(P_i), length(P_i))
    diag(P_i) <- 0

    if (teleport) {
      lambda * P_i + (1 - lambda) / N * matrix(1, N, N)
    } else {
      P_i
    }
  }

  second_order_fatigue <- function(M, ...) {
    kwargs <- list(...)
    lambda <- ifelse(is.null(kwargs$lambda), 0.85, kwargs$lambda)
    N <- nrow(M)

    P_i <- rowSums(M)
    P_i <- 1 - 1 / (P_i + 1)

    # Always consider teleport or else, without smoothing, we'll have "stupid" zeros.
    P_i <- lambda * P_i + (1 - lambda) / N

    P_Ni <- apply(M, 1, function(row) prod(P_i[which(row > 0)]))

    P_Ni_i <- vapply(1:vcount(g), function(i) {
      p <- rep((1 - lambda) / N, vcount(g))
      rw_visits <- as.data.frame(table(random_walk(g, start=i, steps=100)))
      p[as.integer(rw_visits$Var1)] <- lambda * (1 - 1 / (rw_visits$Freq + 1)) + p[as.integer(rw_visits$Var1)]
      prod(p)
    }, 1)

    NF <- (P_i * P_Ni_i) / P_Ni
    NF <- matrix(rep(NF, length(NF)), length(NF), length(NF))
    diag(NF) <- 0
    NF
  }
  
  third_order_fatigue <- function(M, ...) {
    kwargs <- list(...)
    lambda <- ifelse(is.null(kwargs$lambda), 0.85, kwargs$lambda)
    N <- nrow(M)

    P_i <- rowSums(M)
    P_i <- 1 - 1 / (P_i + 1)

    # Always consider teleport or else, without smoothing, we'll have "stupid" zeros.
    P_i <- lambda * P_i + (1 - lambda) / N

    P_Ni <- apply(M, 1, function(row) prod(P_i[which(row > 0)]))

    P_NNi <- apply(M, 1, function(row) prod(P_i[which(row > 0)], apply(M, 2, function(col) prod(P_i[which(col > 0)]))))

    P_Ni_NNi <- P_Ni * P_NNi

    P_Ni_i <- vapply(1:vcount(g), function(i) {
      p <- rep((1 - lambda) / N, vcount(g))
      rw_visits <- as.data.frame(table(random_walk(g, start=i, steps=100)))
      p[as.integer(rw_visits$Var1)] <- lambda * (1 - 1 / (rw_visits$Freq + 1)) + p[as.integer(rw_visits$Var1)]
      prod(p)
    }, 1)

    P_NNi_i <- vapply(1:vcount(g), function(i) {
      p <- rep((1 - lambda) / N, vcount(g))
      rw_visits <- lapply(
        as.numeric(adjacent_vertices(g, i, "in")[[1]]),
        function(j) as.data.frame(table(random_walk(g, start=i, steps=10)))
      )
      if (length(rw_visits) == 0) return(prod(p))
      rw_visits <- aggregate(Freq~Var1, do.call(rbind, rw_visits), sum)
      p[as.integer(rw_visits$Var1)] <- lambda * (1 - 1 / (rw_visits$Freq + 1)) + p[as.integer(rw_visits$Var1)]
      prod(p)
    }, 1)

    P_Ni_NNi_i <- P_Ni_i * P_NNi_i

    NF <- (P_i * P_Ni_NNi_i) / P_Ni_NNi
    NF <- matrix(rep(NF, length(NF)), length(NF), length(NF))
    diag(NF) <- 0
    NF
  }

  # Columns must represent outgoing links
  M <- t(as.matrix(as_adj(g)))
  
  if (fatigue_method == '1ord') {
    NF <- first_order_fatigue(M, ...)
  } else if (fatigue_method == '2ord') {
    NF <- second_order_fatigue(M, ...)
  } else if (fatigue_method == '3ord') {
    NF <- third_order_fatigue(M, ...)
  }

  M <- scale(M, center=FALSE, scale=colSums(M))
  M[is.nan(M)] <- 0
  
  N <- vcount(g)
  
  v <- as.matrix(runif(N))
  v <- v / norm(v)
  last_v <- matrix(1, N) * 100
  
  M_hat <- (d * M + (1-d)/N * matrix(1, N, N)) * (1 - NF)
  
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

# g <- make_graph("Zachary")
# g <- make_graph(c(1,2, 2,3, 3,2, 4,2, 4,3, 3,1, 4,5, 5,3, 3,6, 6,7, 7,8, 8,1, 8,3))
# g <- make_graph(c(1,2, 2,4, 4,3, 3,2))
g <- read_graph(gzfile("~/Data/facebook_combined.txt.gz"), format = "edgelist")

V(g)$pr <- page_rank(g)$vector

pr_sim <- page_rank_simulation(g, steps=1000)
V(g)$pr_sim <- pr_sim$vector
V(g)$pr_sim_iter <- pr_sim$iterationsq
cor(V(g)$pr, V(g)$pr_sim, method="pearson")
cor(V(g)$pr, V(g)$pr_sim, method="spearman")

# pr_iter <- page_rank_power_iteration(g)
# V(g)$pr_iter <- pr_iter$vector
# V(g)$pr_iter_iter <- pr_iter$iterations
# cor(V(g)$pr, V(g)$pr_iter, method="pearson")
# cor(V(g)$pr, V(g)$pr_iter, method="spearman")
 
fpr_sim <- fatigued_page_rank_simulation(g, steps=1000, use_teleport = FALSE)
V(g)$fpr_sim <- fpr_sim$vector
V(g)$fpr_sim_iter <- fpr_sim$iterations
cor(V(g)$pr, V(g)$fpr_sim, method="pearson")
cor(V(g)$pr, V(g)$fpr_sim, method="spearman")

# l <- layout.fruchterman.reingold(g)
# plot(g, layout=l, vertex.size=V(g)$pr * 100, vertex.label=round(V(g)$pr, 2), vertex.label.dist=3)
# title("PR")
# plot(g, layout=l, vertex.size=V(g)$pr_sim * 100, vertex.label=round(V(g)$pr_sim, 2), vertex.label.dist=3)
# title("PR Sim")
# plot(g, layout=l, vertex.size=V(g)$fpr_sim * 100, vertex.label=round(V(g)$fpr_sim, 2), vertex.label.dist=3)
# title("FPR")

# fpr_iter <- fatigued_page_rank_power_iteration(g, fatigue_method = "2ord", teleport=TRUE)
# V(g)$fpr_iter <- fpr_iter$vector
# V(g)$fpr_iter_iter <- fpr_iter$iterations
# cor(V(g)$fpr_sim, V(g)$fpr_iter, method="pearson")
# cor(V(g)$fpr_sim, V(g)$fpr_iter, method="spearman")
# cor(V(g)$pr, V(g)$fpr_sim, method="pearson")
# cor(V(g)$pr, V(g)$fpr_sim, method="spearman")
# cor(V(g)$pr, V(g)$fpr_iter, method="pearson")
# cor(V(g)$pr, V(g)$fpr_iter, method="spearman")

write_graph(g, file = "~/facebook_combined-with_pr_and_fpr.graphml", format = "graphml")


# -------------------------------------------------------------------------------------------------------------------#
#
# MAIN
#

#g <- read.graph(gzfile("/opt/army-ant/output/amazon-meta-simnet.gml.gz"), format = "gml")
#V(g)$pr <- page_rank(g, directed = TRUE)$vector
#V(g)$pr_sim <- page_rank_simulation(g)
#V(g)$fpr <- fatigued_page_rank(g)

# TODO Extract ranks before correlating? Nope. Spearman does this already!
#cor(V(g)$pr, V(g)$fpr, method = "spearman")

