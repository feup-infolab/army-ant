function ScoreComponents(results, selector) {
  this.components = ScoreComponents.resultsToComponents(results);
  this.numDocs = ScoreComponents.countUniqueDocIDs(this.components);
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
  return Array.prototype.concat.apply([], components).reverse();
}

ScoreComponents.countUniqueDocIDs = function(components) {
  var docIDs = {};
  for (var i=0; i < components.length; i++) {
    docIDs[components[i].docID] = true;
  }
  return Object.keys(docIDs).length;
}

ScoreComponents.prototype.render = function() {
  var colors = d3.scale.category10();

  console.log(this.components);
  $(this.selector).css('height', (this.numDocs * 1.5) + 'em');

  // interact with this variable from a javascript console
  var plot = d3.parcoords()(this.selector)
    .data(this.components)
    .margin({ top: 24, left: 230, bottom: 12, right: 0 })    
    .color(function(d) { return colors(d.docID); })
    .alpha(0.8)
    //.smoothness(.2)
    .render()
    .brushMode("1D-axes")  // enable brushing
    .interactive(); // command line mode  

  plot.svg.selectAll("text")
    .style("font", "10px sans-serif");
}
