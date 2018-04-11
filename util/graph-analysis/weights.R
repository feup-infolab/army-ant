source('setup.R')

plot_weights_per_type <- function(data) {
  data <- aggregate(Weight~Type, data)

  ggplot(data, aes(x=Weight)) +
    #geom_histogram(aes(y = (..count..)/tapply(..count.., ..PANEL.., sum)[..PANEL..]), binwidth = 0.05) +
    geom_bar(stat = 'identity') +
    facet_wrap(~Type) +
    scale_y_continuous(label=scales::percent) +
    ylab("Frequency")
}

base_dir <- '/opt/army-ant/analysis/inex_3t_nl-hgoe-weights/syns-context-weighted'

nodes <- read.csv(paste(base_dir, 'node-weights.csv', sep='/'))
edges <- read.csv(paste(base_dir, 'edge-weights.csv', sep='/'))

plot_weights_per_type(nodes)
plot_weights_per_type(edges)