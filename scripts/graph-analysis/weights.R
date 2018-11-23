source('setup.R')

binwidth <- 0.05

plot_weights_per_type <- function(data) {
  data <- split(data, data$Type)
  data <- lapply(data, function(d) {
    df <- as.data.frame(table(cut(d$Weight, seq(0, 1, binwidth), seq(0, 1-binwidth, binwidth))))
    names(df) <- c("BinStart", "Freq")
    df$BinStart <- as.numeric(as.character(df$BinStart))
    df$Freq <- df$Freq / sum(df$Freq)
    cbind(df, Type=unique(d$Type))
  })
  data <- do.call(rbind, data)

  ggplot(data, aes(x=BinStart + binwidth/2, y=Freq, width = binwidth)) +
    geom_bar(stat = 'identity') +
    facet_wrap(~Type) +
    scale_x_continuous(breaks=seq(0, 1.0, 0.2)) +
    scale_y_continuous(label=scales::percent) +
    xlab("Weight") +
    ylab("Frequency")
}

base_dir <- '/opt/army-ant/analysis/inex_52t_nl-hgoe-weights'

nodes <- read.csv(paste(base_dir, 'node-weights.csv', sep='/'), stringsAsFactors = F)
edges <- read.csv(paste(base_dir, 'edge-weights.csv', sep='/'), stringsAsFactors = F)

nodes[which(nodes$Type == 'DocumentNode'), 'Type'] <- 'document'
nodes[which(nodes$Type == 'EntityNode'), 'Type'] <- 'entity'
nodes[which(nodes$Type == 'TermNode'), 'Type'] <- 'term'

edges[which(edges$Type == 'ContainedInEdge'), 'Type'] <- 'contained_in'
edges[which(edges$Type == 'ContextEdge'), 'Type'] <- 'context'
edges[which(edges$Type == 'RelatedToEdge'), 'Type'] <- 'related_to'
edges[which(edges$Type == 'DocumentEdge'), 'Type'] <- 'document'
edges[which(edges$Type == 'RelatedToEdge'), 'Type'] <- 'related_to'
edges[which(edges$Type == 'SynonymEdge'), 'Type'] <- 'synonym'

plot_weights_per_type(nodes)
ggsave("output/node_weight_distr.pdf", width = 7, height = 2.5)
plot_weights_per_type(edges)
ggsave("output/hyperedge_weight_distr.pdf", width = 7, height = 4.5)