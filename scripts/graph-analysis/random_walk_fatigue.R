if (!require("pacman")) install.packages("pacman")

pacman::p_load(
  igraph,
  ggplot2,
  tidyr,
  dplyr,
  foreach,
  logging,
  Matrix,
  xtable
)

# library(igraph)
# library(Matrix)
# library(logging)

basicConfig()

options(stringsAsFactors=FALSE)

if (Sys.info()[["sysname"]] == "Windows") {
  loginfo("Using doParallel for parallelization")
  doParallel::registerDoParallel(cores = parallel::detectCores() - 1)
} else {
  loginfo("Using doMC for parallelization")
  doMC::registerDoMC(cores = parallel::detectCores() - 1)
}

# -------------------------------------------------------------------------------------------------------------------#
#
# PageRank (Simulation)
#

page_rank_simulation <- function(g, d=0.85, steps=10000, PR = NULL) {
  # for (i in 1:vcount(g)) {
  #   cat("==> Walking", steps, "random steps from node", i, "with teleport\n")
  #   PR <- page_rank_simulation_iter(g, start=i, d=d, steps=steps, PR = PR)
  # }

  PR <- foreach (i = 1:vcount(g), .combine=`+`) %dopar% {
    page_rank_simulation_iter(g, start=i, d=d, steps=steps)
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
  # for (i in 1:vcount(g)) {
  #   teleport_str <- ifelse(use_teleport, "teleport", "without teleport")
  #   cat("==> Walking", steps, "random steps from node", i, "with fatigue and", teleport_str, "\n")
  #   FPR <- fatigued_page_rank_simulation_iter(g, i, d=d, nf=nf, steps=steps, use_teleport = use_teleport, FPR = FPR)
  # }

  merge_fpr <- function(a, b) {
    list(
      vector=a$vector + b$vector,
      NF=a$NF + b$NF,
      iterations=a$iterations + b$iterations)
  }

  FPR <- foreach (i = 1:vcount(g), .combine=merge_fpr) %dopar% {
    teleport_str <- ifelse(use_teleport, "teleport", "without teleport")
    cat("==> Walking", steps, "random steps from node", i, "with fatigue and", teleport_str, "\n")
    fatigued_page_rank_simulation_iter(g, i, d=d, nf=nf, steps=steps, use_teleport = use_teleport)
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
fatigued_page_rank_power_iteration <- function(g, d=0.85, nf=10, eps=0.001, fatigue_method='3ord', ...) {
  stopifnot(fatigue_method %in% c('1ord', '2ord', '3ord', 'out_in', 'out_indegree'))

  first_order_fatigue <- function(M, ...) {
    kwargs <- list(...)
    lambda <- ifelse('lambda' %in% kwargs, kwargs$lambda, 0.85)
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
        as.numeric(adjacent_vertices(g, i, 'in')[[1]]),
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

  regular_power_iteration <- function() {
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
      if (norm(v - last_v, '2') <= eps) break;
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

  # TODO optimize with sparse matrices and compare with degree version
  out_in_power_iteration <- function() {
    # Vertex number.
    n <- vcount(g)

    # Column-vector of ones.
    e <- Matrix(1, n)

    # Stochastic matrix from adjacency matrix, with zero columns replaced by teleport probability.
    # This is not explicitly computed, as to avoid storing more values in memory than necessary.
    # Instead, we store H as a sparse matrix and then do this calculation during PageRank vector computation.
    # S <- H + (1/n * e) %*% a

    H_out <- t(as_adj(g))
    H_out <- as(H_out, "dgTMatrix")
    H_out@x <- H_out@x / colSums(H_out)[H_out@j + 1]
    a_out <- Matrix(0, nrow=n)
    idx_zeros <- setdiff(1:n, unique(H_out@j+1))
    if (length(idx_zeros) > 0) {
      a_out[idx_zeros, ] <- 1
    }

    H_in <- as_adj(g)
    H_in <- as(H_in, "dgTMatrix")
    H_in@x <- H_in@x / colSums(H_in)[H_in@j + 1]
    a_in <- Matrix(0, nrow=n)
    idx_zeros <- setdiff(1:n, unique(H_in@j+1))
    if (length(idx_zeros) > 0) {
      a_in[idx_zeros, ] <- 1
    }

    v <- Matrix(runif(n))
    v <- v / norm(v)
    last_v <- Matrix(1/n, n)

    iter <- 0
    repeat {
      if (norm(v - last_v, '2') <= eps) break;
      last_v <- v
      v <- (d*H_out + (d*a_out + (1-d)*e) %*% (1/n * t(e))) %*% v
      v <- v / norm(v)
      iter <- iter + 1
      if (iter %% 1000 == 0) {
        logwarn("FPR power iteration has reached iteration %d", iter)
      }
    }

    list(
      iterations=iter,
      vector=as.numeric(v)
    )
  }

  # Using nomenclature from http://www.cs.cmu.edu/~elaw/pagerank.pdf, except for alpha, which is still d here.
  out_indegree_power_iteration <- function() {
    # Vertex number.
    n <- vcount(g)

    # Column-vector of ones.
    e <- Matrix(1, n)

    # Stochastic matrix from adjacency matrix, with zero columns replaced by teleport probability.
    # This is not explicitly computed, as to avoid storing more values in memory than necessary.
    # Instead, we store H as a sparse matrix and then do this calculation during PageRank vector computation.
    # S <- H + (1/n * e) %*% a

    H <- t(as_adj(g))
    H <- as(H, "dgTMatrix")
    H@x <- H@x / colSums(H)[H@j + 1]
    a <- Matrix(0, nrow=n)
    idx_zeros <- setdiff(1:n, unique(H@j+1))
    if (length(idx_zeros) > 0) {
      a[idx_zeros, ] <- 1
    }

    # Additive smoothing (a.k.a. Laplace smoothing) of the normalized indegree as a stochastic vector
    alpha <- 0.1
    inv_deg_in <- degree(g, mode = "in", normalized = FALSE)
    inv_deg_in <- 1 - (inv_deg_in + alpha) / ((n-1) + alpha*sum(inv_deg_in))
    inv_deg_in <- inv_deg_in / sum(inv_deg_in)

    H <- as(inv_deg_in * H, "dgTMatrix")
    H@x <- H@x / colSums(H)[H@j + 1]

    v <- Matrix(1/n, n)
    batch_size <- 100

    iter <- 0
    repeat {
      last_v <- v
      v <- foreach (i = 1:ceiling(n / batch_size), .combine=rbind, .inorder = TRUE) %dopar% {
        start <- (i-1) * batch_size + 1
        end <- min(i * batch_size, n)
        (d*H[start:end, ] + (d*a[start:end] + (1-d)*e[start:end]) %*% (1/n * t(e))) %*% last_v
      }
      #v <- (d*H + (d*a + (1-d)*e) %*% (1/n * t(e))) %*% v
      #v <- (d * (H + 1/n * a %*% t(e)) + (1-d) * 1/n * e %*% t(e)) %*% last_v
      v <- v / norm(v)

      iter <- iter + 1
      if (iter %% 1000 == 0) {
        logwarn("FPR power iteration has reached iteration %d", iter)
      }

      if (norm(v - last_v, '2') <= eps) break;
    }

    list(
      iterations=iter,
      vector=as.numeric(v)
    )
  }

  if (fatigue_method == 'out_in') {
    out_in_power_iteration()
  } else if (fatigue_method == 'out_indegree') {
    out_indegree_power_iteration()
  } else {
    regular_power_iteration()
  }
}

plot_replicas_histogram <- function(df) {
  p <- ggplot(NULL, aes(x=value, fill=key)) +
    scale_x_continuous() +
    scale_y_log10() +
    scale_fill_discrete("Replica") +
    xlab("Metric") +
    ylab("Frequency")

  for (i in 1:ncol(df)) {
    data <- df[, i, drop=FALSE] %>% gather() %>% filter(value > 0)
    p <- p + geom_histogram(
      bins = 20,
      data = data,
      alpha = 0.25)
  }

  p
}

plot_small_graph_with_metrics <- function(g, metrics=list("PR"="pr", "PR Sim"="pr_sim", "FPR Sim"="fpr_sim")) {
  l <- layout.fruchterman.reingold(g)
  for (name in names(metrics)) {
    plot(
      g, layout=l,
      vertex.size=get.vertex.attribute(g, metrics[[name]]) * 100,
      vertex.label=round(get.vertex.attribute(g, metrics[[name]]), 2),
      vertex.label.dist=3)
    title(name)
  }
}

toy_example <- function() {
  print_latex_matrix <- function(m, digits=0) {
    m <- as.matrix(m)
    x <- xtable(m, align=rep("", ncol(m)+1), digits=digits)
    print(
      x, floating=FALSE, tabular.environment="bmatrix",
      hline.after=NULL, include.rownames=FALSE, include.colnames=FALSE)
  }

  g <- make_graph(c(1,2, 2,3, 3,1, 4,1, 4,3, 4,5, 6,4, 6,7))
  n <- vcount(g)

  cat("\n==> Plot\n")
  set.seed(1337)
  pdf(file = "output/fatigued_pagerank-toy_example_graph.pdf", width = 5, height = 5)
  plot(g, vertex.color="#ecd078", vertex.size=30)
  dev.off()

  cat("\n==> Adjacency\n")
  A <- as_adj(g)
  print_latex_matrix(A)

  cat("\n==> H\n")
  H <- t(as_adj(g))
  H <- as(H, "dgTMatrix")
  H@x <- H@x / colSums(H)[H@j + 1]
  print_latex_matrix(H, digits=2)

  cat("\n==> a^T\n")
  a <- Matrix(0, nrow=n)
  a[setdiff(1:n, unique(H@j+1)), ] <- 1
  print_latex_matrix(t(a))

  # TODO generate prints for remaining

  # Additive smoothing (a.k.a. Laplace smoothing) of the normalized indegree as a stochastic vector
  alpha <- 0.1
  inv_deg_in <- degree(g, mode = "in", normalized = FALSE)
  inv_deg_in <- 1 - (inv_deg_in + alpha) / ((n-1) + alpha*sum(inv_deg_in))
  inv_deg_in <- inv_deg_in / sum(inv_deg_in)

  v <- Matrix(runif(n))
  v <- v / norm(v)
  last_v <- Matrix(1/n, n)

  H <- as(inv_deg_in * H, "dgTMatrix")
  H@x <- H@x / colSums(H)[H@j + 1]
}
#toy_example()

# -------------------------------------------------------------------------------------------------------------------#
#
# MAIN
#

#
# Graph
#

# g <- make_graph("Zachary")
# g <- make_graph(c(1,2, 2,3, 3,2, 4,2, 4,3, 3,1, 4,5, 5,3, 3,6, 6,7, 7,8, 8,1, 8,3))
# g <- make_graph(c(1,2, 2,3, 3,1, 4,1, 4,3, 4,5, 6,4, 6,7))
# g <- make_graph(c(1,2, 2,4, 4,3, 3,2))
# g <- read_graph(gzfile("~/Data/facebook_combined.txt.gz"), format = "edgelist")

# system.time(
#   g <- read_graph(
#     gzfile("~/Data/wikipedia/simplewiki_link_graph-article_namespace-with_transitions-20190201T1204.gml.gz"),
#     "gml"))
# system.time(names(edge_attr(g))[which(names(edge_attr(g)) == "transitions")] <- "weight")
# save(g, file = "/media/vdb1/output/simplewiki_link_graph-article_namespace-with_transitions-20190201T1204.RData")

#system.time(load("/media/vdb1/output/simplewiki_link_graph-article_namespace-with_transitions-20190201T1204.RData"))
system.time(load("~/Data/wikipedia/simplewiki_link_graph-article_namespace-with_transitions-20190201T1204.RData"))

#
# Node ranking metrics
#

system.time(V(g)$indegree <- degree(g, mode = "in"))
system.time(V(g)$pr <- page_rank(g)$vector)
system.time(V(g)$hits_authority <- authority_score(g)$vector)

# pr_sim <- page_rank_simulation(g, steps=1000)
# V(g)$pr_sim <- pr_sim$vector
# V(g)$pr_sim_iter <- pr_sim$iterations
#
# pr_iter <- page_rank_power_iteration(g)
# V(g)$pr_iter <- pr_iter$vector
# V(g)$pr_iter_iter <- pr_iter$iterations
#
# system.time(fpr_sim <- fatigued_page_rank_simulation(g, steps=1000, use_teleport = TRUE))
# V(g)$fpr_sim <- fpr_sim$vector
# V(g)$fpr_sim_iter <- fpr_sim$iterations
#
# system.time(fpr_sim_without_teleport <- fatigued_page_rank_simulation(g, steps=1000, use_teleport = FALSE))
# V(g)$fpr_sim_without_teleport <- fpr_sim_without_teleport$vector
# V(g)$fpr_sim_without_teleport_iter <- fpr_sim_without_teleport$iterations

system.time(fpr_out_indegree <- fatigued_page_rank_power_iteration(g, fatigue_method = "out_indegree"))
V(g)$fpr_out_indegree <- fpr_out_indegree$vector
V(g)$fpr_out_indegree_iter <- fpr_out_indegree$iterations

eval <- list(
  indegree=c(
    pearson=cor(strength(g, mode = "in"), degree(g, mode = "in"), method = "pearson"),
    spearman=cor(strength(g, mode = "in"), degree(g, mode = "in"), method = "spearman")),
  pr=c(
    pearson=cor(strength(g, mode = "in"), V(g)$pr, method = "pearson"),
    spearman=cor(strength(g, mode = "in"), V(g)$pr, method = "spearman")),
  hits_authority=c(
    pearson=cor(strength(g, mode = "in"), V(g)$hits_authority, method = "pearson"),
    spearman=cor(strength(g, mode = "in"), V(g)$hits_authority, method = "spearman")),
  fpr_out_indegree=c(
    pearson=cor(strength(g, mode = "in"), V(g)$fpr_out_indegree, method = "pearson"),
    spearman=cor(strength(g, mode = "in"), V(g)$fpr_out_indegree, method = "spearman"))
)
eval

save.image()
