#
# This is a Shiny web application. You can run the application by clicking
# the 'Run App' button above.
#
# Find out more about building applications with Shiny here:
#
#    http://shiny.rstudio.com/
#

source('setup.R')
library(shiny)

functions_library <- list(
  sigmoid=sigmoid,
  log10=log10,
  sec=function(x) 1/cos(x),
  cot=function(x) 1/tan(x)
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
          'sigmoid(x)'='sigmoid',
          'log10(x)'='log10',
          'sec(x)'='sec',
          'cot(x)'='cot'
        )
      ),
      sliderInput(
        'xMin',
        'min(x):',
        min=-10,
        max=10,
        value=-10,
        step=0.1
      ),
      sliderInput(
        'xMax',
        'max(x):',
        min=-10,
        max=10,
        value=10,
        step=0.1
      ),
      textInput(
        'xAffect',
        'Change value of x:',
        placeholder = 'x * 2 + 1'
      ),
      textInput(
        'yAffect',
        'Change value of y:',
        placeholder = '1 / y'
      )
    ),
    
    # Show a plot of the generated distribution
    mainPanel(plotOutput("plot"))
  )
)

# Define server logic required to draw a histogram
server <- function(input, output) {
  output$plot <- renderPlot({
    x <- seq(input$xMin, input$xMax, 0.01)
    if (input$xAffect != '') {
      x <- eval(parse(text=input$xAffect))
    }
    
    y <- functions_library[[input$func]](x)
    if (input$yAffect != '') {
      y <- eval(parse(text=input$yAffect))
    }
    
    qplot(x, y, geom='line', ylab=input$func, xlim = c(input$xMin, input$xMax))
  })
}

# Run the application
shinyApp(ui = ui, server = server)
