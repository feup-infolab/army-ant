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

functions_library <- list(
  sigmoid=sigmoid,
  log10=log10,
  sec=function(x) 1/cos(x),
  cot=function(x) 1/tan(x),
  'x^2'=function(x) x^2,
  power_law=function(x, a=1, k=1) a*x^(-k)
)

# Define UI for application that draws a histogram
ui <- fluidPage(
  # Application title
  titlePanel("Function Explorer"),
  
  # Sidebar with a slider input for number of bins
  sidebarLayout(
    sidebarPanel(
      selectInput(
        "func",
        "Function:",
        list(
          'f(x, a=1, k=1) = a * x^(-k)'='power_law',
          'f(x) = x^2'='x^2',
          'sigmoid(x)'='sigmoid',
          'log10(x)'='log10',
          'sec(x)'='sec',
          'cot(x)'='cot'
        )
      ),
      numericInput(
        'x_min',
        'min(x):',
        value=-10
      ),
      numericInput(
        'x_max',
        'max(x):',
        value=10
      ),
      textInput(
        'x_affect',
        'Change value of x:',
        placeholder = 'x * 2 + 1'
      ),
      textInput(
        'y_affect',
        'Change value of y:',
        placeholder = '1 / y'
      )
    ),
    
    # Show a plot of the generated distribution
    mainPanel(plotOutput('plot'))
  )
)

# Define server logic required to draw a histogram
server <- function(input, output) {
  output$plot <- renderPlot({
    x <- seq(input$x_min, input$x_max, 0.001)
    if (input$x_affect != '') {
      x <- eval(parse(text=input$x_affect))
    }
    
    y <- functions_library[[input$func]](x)
    if (input$y_affect != '') {
      y <- eval(parse(text=input$y_affect))
    }
    
    qplot(x, y, geom='line', ylab=input$func, xlim = c(input$x_min, input$x_max))
  })
}

# Run the application
#shinyApp(ui = ui, server = server)

#
# Sandbox
#

N <- 2200; n <- seq(0, N); plot(n, sigmoid((N^-.75)*(length(n)-n)/n)*2-1, type='l', xlim=c(0,2200))