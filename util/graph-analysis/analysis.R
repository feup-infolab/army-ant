source('setup.R')

basic_stats <- function(g) {
  data.frame(
    stat=c(
      'nodes',
      'edges',
      'diameter'
    ),
    value=c(
      vcount(g),
      ecount(g),
      diameter(g)
    )
  )
}

plot_distribution <- function(values, attr_name='Weight') {
  ggplot(data.frame(x=values), aes(x=x)) +
    geom_histogram()
}

loginfo("Loading graph")
if (!exists('g') || class(g) != 'igraph') {
  if (endsWith(graphml_file, '.gz')) graphml_file <- gzfile(graphml_file)
  g <- read.graph(graphml_file, format = 'graphml')
  if ('connection' %in% class(graphml_file)) close(graphml_file)
} else {
  logwarn("Using existing graph (remove 'g' and run again if you want to reload)")
}

analysis <- list()

if (!is.null(analysis_setup$basic_stats)) {
  loginfo("Computing basic statistics")
  analysis$stats <- basic_stats(g)
}

if (!is.null(analysis_setup$communities)) {
  loginfo("Running community detection based on label propagation")
  analysis$communities <- label.propagation.community(g)
}

if (!is.null(analysis_setup$plot_edge_weight_distribution)) {
  loginfo("Plotting edge weight distribution")
  analysis$plots$edge_weight_distribution <- ggplot(data.frame(weight=E(g)$weight), aes(x=weight)) +
    geom_histogram(aes(y = ..count../sum(..count..)), binwidth = 0.025, color='lightgray', boundary=-0.5) +
    scale_y_continuous(labels=scales::percent) +
    xlab(analysis_setup$plot_edge_weight_distribution$xaxis) +
    ylab("Frequency")
}

analysis$plots$edge_weight_distribution