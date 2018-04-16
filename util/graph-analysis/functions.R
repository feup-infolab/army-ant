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

sigmoid_idf <- function(N, n) sigmoid((N^-1)*(length(n)-n)/n)*2-1

prob_idf <- function(N, n) log10((N - n) / n)

idf_funcs <- list(
  Sigmoid=sigmoid_idf,
  Probabilistic=prob_idf
)

# Corpus size
N <- 2200

# Random uniform simulation of the number of documents a term appears in (not realistic)
n <- sample(seq(0, N), 1e5, replace = T)

data <- data.frame(n=n)
data <- do.call(rbind, lapply(names(idf_funcs), function(idf_func_name) {
  cbind(data, func=idf_func_name, val=idf_funcs[[idf_func_name]](N, n))
}))

ggplot(data, aes(x=n, y=val, color = func)) +
  geom_line(size=1.1) +
  scale_color_discrete("Variant") +
  xlab(expression(n[t])) +
  ylab("IDF") +
  xlim(0, N) +
  ylim(0, 1) +
  theme(legend.position = 'top')
