function ScoreComponents(components, selector) {
  this.components = components;
  this.selector = selector;
}

ScoreComponents.resultsToComponents = function(results) {
  let components = results.map(function(result) {
    return result.components.map(function(c) {
      let components = {};
      for (var k in c) {
        components[k] = round(c[k], 4);
      }
      return components;
    });
  });
  return Array.prototype.concat.apply([], components);
}

ScoreComponents.prototype.render = function() {
  var colors = d3.scale.category10();

  // interact with this variable from a javascript console
  var plot = d3.parcoords()(this.selector)
    .data(this.components)
    .composite("darken")
    .margin({ top: 24, left: 225, bottom: 12, right: 0 })    
    .color(function(d) { return colors(d.docID); })
    .alpha(0.8)
    .render()
    .brushMode("1D-axes")  // enable brushing
    .interactive(); // command line mode  

  plot.svg.selectAll("text")
    .style("font", "10px sans-serif");
}
