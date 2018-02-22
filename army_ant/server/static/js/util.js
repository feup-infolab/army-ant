function isNumeric(n) {
  return !isNaN(parseFloat(n)) && isFinite(n);
}

function round(value, decimals) {
  if (!isNumeric(value)) return value;
  return Number(Math.round(value+'e'+decimals)+'e-'+decimals);
}

function getQueryStrings() {
  let assoc = {};
  const decode = function (s) {
    return decodeURIComponent(s.replace(/\+/g, " "));
  };
  let queryString = location.search.substring(1);
  let keyValues = queryString.split('&');

  for(let i in keyValues) {
    let key = keyValues[i].split('=');
    if (key.length > 1) {
      assoc[decode(key[0])] = decode(key[1]);
    }
  } 

  return assoc; 
} 
