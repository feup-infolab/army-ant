source('setup.R')

plot_degree_per_type <- function(data, xlab="Degree") {
  data <- split(data, data$Type)
  data <- lapply(data, function(d) cbind(Type=d$Type[1], setNames(as.data.frame(table(d$Degree)), c("Degree", "Freq"))))
  data <- do.call(rbind, data)
  data$Degree <- as.numeric(as.character(data$Degree))
  ggplot(data, aes(x=Degree, y=Freq)) +
    facet_wrap(~Type) +
    geom_point() +
    stat_smooth(method = "loess") +
    scale_x_log10() + 
    scale_y_log10() +
    xlab(xlab) +
    ylab("Frequency")
}

base_dir <- '/opt/army-ant/analysis/inex_2009_3t_nl-degree'

nodes <- read.csv(paste(base_dir, 'node-degree.csv', sep='/'), stringsAsFactors = F)
edges <- read.csv(paste(base_dir, 'edge-degree.csv', sep='/'), stringsAsFactors = F)

nodes[which(nodes$Type == 'DocumentNode'), 'Type'] <- 'document'
nodes[which(nodes$Type == 'EntityNode'), 'Type'] <- 'entity'
nodes[which(nodes$Type == 'TermNode'), 'Type'] <- 'term'

edges[which(edges$Type == 'ContainedInEdge'), 'Type'] <- 'contained_in'
edges[which(edges$Type == 'ContextEdge'), 'Type'] <- 'context'
edges[which(edges$Type == 'RelatedToEdge'), 'Type'] <- 'related_to'
edges[which(edges$Type == 'DocumentEdge'), 'Type'] <- 'document'
edges[which(edges$Type == 'RelatedToEdge'), 'Type'] <- 'related_to'
edges[which(edges$Type == 'SynonymEdge'), 'Type'] <- 'synonym'

plot_degree_per_type(nodes, xlab = "Node Degree")
ggsave("output/node_degree_distr.pdf", width = 5, height = 2)
plot_degree_per_type(edges, xlab = "Hyperedge Degree")
ggsave("output/hyperedge_degree_distr.pdf", width = 5, height = 3.5)