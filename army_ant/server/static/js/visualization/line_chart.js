function LineChart(data, selector) {
  this.data = data;
  this.selector = selector;
}

LineChart.prototype.getPalette = function(n) {
  var scale = d3.scale.ordinal().range(['#5755d9', '#32b643', '#ffb700', '#e85600']);
  var palette = [];
  for (var i=0; i < n; i++) {
    palette.push(scale(i));
  }
}

LineChart.prototype.render = function(activeLengend) {
  var palette = this.getPalette(this.data.length-1);

  var config = {
    bindto: this.selector,
    data: {
      x: this.data[0][0],
      columns: this.data,
      type: 'line'
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
      }
    },
    color: {
      pattern: palette
    },
    padding: {
      top: 50,
      right: 50,
      bottom: -10
    },
    legend: {
      show: true
    },
    size: {
      height: 300
    },
    point: {
      r: 3
    }
  };

  this.chart = c3.generate(config);

  if (activeLengend) {
    this.chart.hide();
    this.chart.show(activeLengend);
  }
}
