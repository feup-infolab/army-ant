#!/usr/bin/Rscript

args <- commandArgs(T)
if (length(args) < 2) {
  cat("Usage: ./top_100_results_per_topic.R INPUT.res[.gz] OUTPUT.res.gz\n")
  quit(save="no", status=1)
}

input <- args[[1]]
output <- args[[2]]

cat("===> Loading", input, "\n")
r2 <- read.table(input, sep=" ")
cat("===> Splitting per topic\n")
r2.split <- split(r2, r2$V1)
cat("===> Sorting per rank in ascending order\n")
r2.split.sorted <- lapply(r2.split, function(res) res[order(res$V4), ])
cat("===> Filtering first 100 results per topic\n")
r2.split.sorted.100 <- lapply(r2.split.sorted, head, 100)
cat("===> Joining results into a single data.frame\n")
r2.join <- do.call(rbind, r2.split.sorted.100)
cat("===> Writing result to", output, "\n")
write.table(r2.join, gzfile(output), sep=" ", quote=F, col.names=F, row.names=F)
cat("===> Done.\n")
