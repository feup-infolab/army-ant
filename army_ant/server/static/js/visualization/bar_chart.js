function BarChart(data, selector) {
  this.data = data;
  this.selector = selector;
}

BarChart.prototype.render = function() {
  this.chart = c3.generate({
    bindto: this.selector,
    data: {
      x: this.data[0][0],
      columns: this.data,
      type: 'bar'
    },
    axis: {
      x: {
        type: 'category'
      },
      y: {
        tick: {
          count: 3,
          format: d3.format('.1f')
        }
      }
    },
    bar: {
      width: {
        ratio: 0.3
      }
    },
    color: {
      pattern: ['#5755d9', '#32b643', '#ffb700', '#e85600']
    },
    padding: {
      top: 5,
      bottom: -10
    },
    legend: {
      show: false
    },
    size: {
      height: 110
    }
  });
}
