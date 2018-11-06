if (!require("pacman")) install.packages("pacman")

pacman::p_load(
  igraph
)

g <- read.graph("~/Downloads/example.net", format = "pajek")