function isNumeric(n) {
  return !isNaN(parseFloat(n)) && isFinite(n);
}

function round(value, decimals) {
  if (!isNumeric(value)) return value;
  return Number(Math.round(value+'e'+decimals)+'e-'+decimals);
}

function getQueryStrings() { 
  var assoc  = {};
  var decode = function (s) { return decodeURIComponent(s.replace(/\+/g, " ")); };
  var queryString = location.search.substring(1); 
  var keyValues = queryString.split('&'); 

  for(var i in keyValues) { 
    var key = keyValues[i].split('=');
    if (key.length > 1) {
      assoc[decode(key[0])] = decode(key[1]);
    }
  } 

  return assoc; 
} 
