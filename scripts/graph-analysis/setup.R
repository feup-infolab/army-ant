#
# setup.R
# <This file only contains libraries, settings and constants.>
#

# Put all dependencies here
if (!require(pacman)) install.packages('pacman')
pacman::p_load(
  igraph,
  ggplot2,
  dplyr,
  logging,
  sigmoid,
  Cairo
)

basicConfig()

# Set this to your own GraphML file (it can optionally be gzip compressed)
graphml_file <- '/opt/army-ant/features/inex_2009_52t_nl-word2vec_simnet/word2vec_simnet.graphml.gz'

analysis_setup <- list(
  basic_stats=NULL,
  communities=NULL,
  plot_edge_weight_distribution=list(xaxis='Term-Term Contextual Similarity')
)