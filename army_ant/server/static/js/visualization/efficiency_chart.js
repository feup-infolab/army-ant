function EfficiencyChart(data, selector) {
  this.data = data;
  this.selector = selector;
}

EfficiencyChart.prototype.render = function() {
  //$(this.selector).css('height', ((this.data[0].length-1) * 30) + 'px');
  
  var config = {
    bindto: this.selector,
    data: {
      x: this.data[0][0],
      columns: this.data,
      type: 'bar',
      labels: false
    },
    size: {
      height: 100
    },
    axis: {
      x: {
        type: 'category',
        show: true
      },
      y: {
        tick: {
          count: 3,
          format: d3.format('.3f')
        }
      },
      rotated: false
    },
    color: {
      pattern: ['#5755d9', '#32b643', '#ffb700', '#e85600']
    },
    padding: {
      top: 5,
      right: 10,
      bottom: -10,
      left: 50
    },
    legend: {
      show: false
    }
  };

  this.chart = c3.generate(config);

  if (this.data[0].length > 5) {
    $(this.selector).find('.c3-axis-x .tick text').css('display', 'none !important');
  }
}
