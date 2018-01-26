function BarChart(data, selector) {
  this.data = data;
  this.selector = selector;
}

BarChart.prototype.render = function() {
  $(this.selector).css('height', ((this.data[0].length-1) * 30) + 'px');

  this.chart = c3.generate({
    bindto: this.selector,
    data: {
      x: this.data[0][0],
      columns: this.data,
      type: 'bar',
      labels: true
    },
    axis: {
      x: {
        type: 'category'
      },
      y: {
        tick: {
          count: 3,
          format: d3.format('.3f')
        }
      },
      rotated: true
    },
    color: {
      pattern: ['#5755d9', '#32b643', '#ffb700', '#e85600']
    },
    padding: {
      top: 5,
      right: 50,
      bottom: -10
    },
    legend: {
      show: false
    }
  });
}
