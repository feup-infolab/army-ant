/**
 * Calculate the TW-IDF, from Graph of Word model, for a term in a document.
 *
 * @param indegree Term vertice indegree.
 * @param docFreq Document frequency of the term. The number of documents containing the term.
 * @param docLength The number of characters of the document.
 * @param avgDocLength The average number of characters of the documents in the corpus.
 * @param corpusSize The number of documents in the corpus.
 * @param b The slope parameter of the tilting. Fixed at 0.003 for TW-IDF.
 */
def twIdf(indegree, docFreq, docLength, avgDocLength, corpusSize, b=0.003) {
  indegree / (1 - b + b * docLength / avgDocLength) * Math.log((corpusSize + 1) / docFreq)
}

graph_of_word_query: {
  query = g.V().has("name", within(queryTokens))

  indegreePerTokenPerDoc = query.clone()
    .project("v", "indegree").by()
    .by(inE().values("doc_id").groupCount())
  
  docFrequencyPerToken = query.clone()
    .project("v", "docFreq").by()
    .by(bothE().groupCount().by("doc_id"))
    .collectEntries { e -> [(e["v"]): e["docFreq"].size()] }

  docLengths = g.E().group().by("doc_id").by(inV().count())

  #avgDocLength = 

  docsIndegreePerToken
}
