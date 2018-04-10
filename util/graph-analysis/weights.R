if (!require(pacman)) install.packages("pacman")
pacman::p_load(
  ggplot2
)

plotWeightsPerType <- function(data) {
  ggplot(data, aes(x=Weight)) +
    geom_histogram(binwidth = 0.1) +
    facet_wrap(~Type) +
    ylab("Frequency")
}

nodes <- read.csv("/tmp/hgoe-export/node-weights-20180410T145239.csv")
edges <- read.csv("/tmp/hgoe-export/edge-weights-20180410T145252.csv")

plotWeightsPerType(nodes)
plotWeightsPerType(edges)