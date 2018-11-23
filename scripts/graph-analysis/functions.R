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

sigmoid_idf <- function(N, n, alpha=-0.75) sigmoid((N^alpha)*(length(n)-n)/n)*2-1

prob_idf <- function(N, n) log10((N - n) / n)

idf_funcs <- list(
  'Sigmoid (α=N^-0.5)'=function(N, n) sigmoid_idf(N, n, alpha=-0.5),
  'Sigmoid (α=N^-0.75)'=function(N, n) sigmoid_idf(N, n, alpha=-0.75),
  'Sigmoid (α=N^-1)'=function(N, n) sigmoid_idf(N, n, alpha=-1),
  'Probabilistic'=prob_idf
)

#
# Common
#

plot_funcs <- function(funcs, params) {
  data <- data.frame(x=params$n)
  data <- do.call(rbind, lapply(names(funcs), function(func_name) {
    cbind(data, func=func_name, y=do.call(funcs[[func_name]], params))
  }))
  
  ggplot(data, aes(x=x, y=y, color = func)) +
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
N <- 2000

# Random uniform simulation of the number of documents a term appears in (not realistic)
n <- sample(seq(0, N), 1e5, replace = T)

idf_p <- plot_funcs(idf_funcs, list(N=N, n=n)) +
  xlab("Number of Documents") +
  ylab("IDF") +
  xlim(0, N) +
  ylim(-0.25, 1.25)

print(idf_p)
ggsave(filename = "output/idf_funcs.pdf", plot = idf_p, width = 7, height = 3, device=cairo_pdf)