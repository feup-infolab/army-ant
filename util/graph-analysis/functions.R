#
# This is a Shiny web application. You can run the application by clicking
# the 'Run App' button above.
#
# Find out more about building applications with Shiny here:
#
#    http://shiny.rstudio.com/
#

#
# Meh, this sucks... Just plot the damn thing instead.
#

source('setup.R')
library(shiny)

#
# IDF Functions
#

sigmoid_idf <- function(N, n) sigmoid((N^-1)*(length(n)-n)/n)*2-1

prob_idf <- function(N, n) log10((N - n) / n)

idf_funcs <- list(
  Sigmoid=sigmoid_idf,
  Probabilistic=prob_idf
)

#
# Common
#

plot_funcs <- function(funcs, params) {
  data <- data.frame(n=n)
  data <- do.call(rbind, lapply(names(funcs), function(func_name) {
    cbind(data, func=func_name, val=do.call(funcs[[func_name]], params))
  }))
  
  ggplot(data, aes(x=n, y=val, color = func)) +
    geom_line(size=1.1) +
    scale_color_discrete("Function") +
    xlab("x") +
    ylab("y") +
    theme(legend.position = 'top')  
}

#
# Main
#

# Corpus size
N <- 2200

# Random uniform simulation of the number of documents a term appears in (not realistic)
n <- sample(seq(0, N), 1e5, replace = T)

plot_funcs(idf_funcs, list(N=N, n=n)) + xlim(0, N)+ ylim(0, 1)