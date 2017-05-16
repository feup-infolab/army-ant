function isNumeric(n) {
  return !isNaN(parseFloat(n)) && isFinite(n);
}

function round(value, decimals) {
  if (!isNumeric(value)) return value;
  return Number(Math.round(value+'e'+decimals)+'e-'+decimals);
}
