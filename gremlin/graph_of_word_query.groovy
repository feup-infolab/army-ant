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

//queryTokens = ['born', 'new', 'york']
//queryTokens = ['soziale', 'herkunft']
//offset = 0
//limit = 10

graph_of_word_query: {
  query = g.V().has("name", within(queryTokens))

  if (query.clone().count().next() < 1) return [[results: [:], numDocs: 0]]

  indegreePerTokenPerDoc = query.clone()
    .group()
      .by()
      .by(inE().values("doc_id").groupCount())
    .next()
  
  docFrequencyPerToken = query.clone()
    .group()
      .by()
      .by(bothE().values("doc_id").dedup().count())
    .next()

  docLengths = g.E()
    .group()
      .by("doc_id")
      .by(inV().count())
    .next()

  if (docLengths.isEmpty()) return [[results: [:], numDocs: 0]]

  avgDocLength = docLengths.values().sum() / docLengths.size()
  
  corpusSize = g.E().values("doc_id").dedup().count().next()

  twIdf = indegreePerTokenPerDoc.collect { token, indegreePerDoc ->
      indegreePerDoc.collect { docID, indegree ->
        score = twIdf(indegree, docFrequencyPerToken[token], docLengths[docID], avgDocLength, corpusSize)

        [
          docID: docID,
          twIdf: score,
          components: [
            docID: docID,
            'tw(t, d)': indegree,
            b: 0.003d,
            '|d|': docLengths[docID],
            avdl: avgDocLength.doubleValue(),
            N: corpusSize,
            'df(t)': docFrequencyPerToken[token],
            'tw-idf(t, d)': score
          ]
        ]
      }
    }
    .flatten()
    .groupBy { item -> item['docID'] }
    .collect { docID, item -> [docID: docID, score: item['twIdf'].sum(), components: item['components']] }
    .sort { -it.score }

  numDocs = twIdf.size()

  twIdf = twIdf
    .drop(offset)
    .take(limit)

  [[results: twIdf, numDocs: numDocs]]
}
