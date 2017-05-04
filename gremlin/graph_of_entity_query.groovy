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
def nwIdf(nodeWeight, docFreq, docLength, avgDocLength, corpusSize, b=0.003) {
  nodeWeight / (1 - b + b * docLength / avgDocLength) * Math.log((corpusSize + 1) / docFreq)
}

//queryTokens = ['born', 'new', 'york']
//queryTokens = ['nirvana', 'members']
//offset = 0
//limit = 10

graph_of_entity_query: {
  query = g.withSack(0f).V().has("name", within(queryTokens))

  docFrequencyPerToken = query.clone()
    .project("v", "docFreq")
    .by()
    .by(bothE().has("doc_id").groupCount().by("doc_id"))
    .collectEntries { e -> [(e["v"]): e["docFreq"].size()] }

  docLengthsPipe = g.E()
    .has("doc_id")
    .group()
      .by("doc_id")
      .by(inV().count())

  docLengths = []

  docLengthsPipe.clone().fill(docLengths)

  if (docLengths.isEmpty()) return []

  avgDocLength = docLengthsPipe.clone()[0].values().sum() / docLengthsPipe.clone()[0].values().size()
  
  corpusSize = g.E()
    .has("doc_id")
    .values("doc_id")
    .unique()
    .size()  

  seedScoresPipe = query.clone()
    .union(
      __.out("contained_in"),
      __.where(__.not(out("contained_in"))))
    .dedup()
    .choose(
      has("type", "entity"),
      group()
        .by()
        .by(
          fold()
            .sack(sum).by(count(local))
            .sack(div).by(unfold().in("contained_in").dedup().count())
            .sack()
        ),
      group()
        .by()
        .by(constant(1d))
    )
    .unfold()
    .order()
    .by(values, decr)

  seedScores = seedScoresPipe.clone()
    .collectEntries { [(it.key): (it.value)] }

  maxDistance = 2

  distancesToSeedsPerEntity = seedScoresPipe.clone().select(keys).as("seed")
    .repeat(both().where(neq("seed")))
    .times(maxDistance)
    .where(has("type", "entity"))
    .path().as("path")
    .project("entity", "seed", "distance")
      .by { it.getAt(maxDistance+2) }
      .by { it.getAt(2) }
      .by(sack(assign).by(count(local)).sack(sum).by(constant(-2)).sack())
    .group()
      .by(select("entity"))
      .by(group().by(select("seed")).by(select("distance").fold()))
    .unfold()

  //return distancesToSeedsPerEntity.collectEntries { [(it.key.value("name")): it.value] }

  nodeWeights = distancesToSeedsPerEntity.clone()
    .collect {
      docID = "http://en.wikipedia.org/wiki/${it.key.value("name").replace(" ", "_")}"
      //seedCount = it.value.size()
      coverage = it.value.size() / seedScores.size()

      weight = it.value.collect { d ->
        a = d.value.collect { v ->
          seedScores.get(d.key, 0f) * 1f / v
        }
        a.sum() / a.size()
      }
      weight = coverage * weight.sum() / weight.size()

      // TODO implement docFrequentyPerNode (terms and entities) to apply nwIdf 
      [docID: docID.toString(), score: weight]
    }
    .sort { -it.score }
    .drop(offset)
    .take(limit)

  [[results: nodeWeights, numDocs: distancesToSeedsPerEntity.clone().count().next()]]
}
