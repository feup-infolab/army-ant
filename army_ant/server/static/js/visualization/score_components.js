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
  var colors = d3.scale.category20();

  // interact with this variable from a javascript console
  var pc1 = d3.parcoords()(this.selector)
    .data(this.components)
    .hideAxis(["docID"])
    //.composite("darken")
    .color(function(d) { return colors(d.docID); })
    .alpha(0.8)
    .render()
    .brushMode("1D-axes")  // enable brushing
    .interactive(); // command line mode  
}
