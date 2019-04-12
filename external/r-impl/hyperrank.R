source("preprocessing.R")

open_index <- function(path) {
  idx <- matrix(10, 10)
  class(idx) <- "hyperrank"
  idx
}

print.hyperrank <- function(obj) {
  cat("HyperRank index of dimension", paste(dim(obj), collapse = "x"))
}

index_batch <- function(docs) {
  corpus <- Corpus(VectorSource(sapply(docs, `[`, "text")))
  docs <- analyze(corpus)
}
