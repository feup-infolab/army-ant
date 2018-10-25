function EffectivenessChart(data, selector) {
  this.data = data;
  this.selector = selector;
}

EffectivenessChart.prototype.getPalette = function(n) {
  var step = d3.scale.linear()
    .domain([1, n])
    .range([1, 50]);
  
  var domain = [];
  for (var i=1; i < n; i++) {
    domain.push(step(i));
  }

  var scale = d3.scale.linear()
    .domain(domain)
    .range(['#5755d9', '#32b643', '#ffb700', '#e85600'])
    .interpolate(d3.interpolateHsl);

  var palette = [];
  for (var i=0; i < n; i++) {
    palette.push(scale(i));
  }

  var reorderedPalette = [];
  for (var i=0; i < palette.length; i++) {
    for (var j=i; j < palette.length; j+=4) {
      reorderedPalette.push(palette[j]);
    }
  }

  return reorderedPalette;
}

EffectivenessChart.prototype.render = function(activeLengend) {
  var palette = this.getPalette(this.data.length-1);

  var config = {
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
      bottom: 20
    },
    legend: {
      show: true,
      inset: {
        anchor: 'top-right',
        x: 10,
        y: 0,
        step: 5
      }
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

  if (this.data[0].length > 5) {
    $(this.selector).find('.c3-axis-x .tick text').css('display', 'none !important');
  }
}
