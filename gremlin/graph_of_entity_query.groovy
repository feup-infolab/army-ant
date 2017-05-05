/**
 * Calculate the EW-ILE, from Graph of Entity model, for an entity node linked to a seed node.
 *
 * @param indegree Term vertice indegree.
 * @param docFreq Document frequency of the term. The number of documents containing the term.
 * @param docLength The number of characters of the document.
 * @param avgDocLength The average number of characters of the documents in the corpus.
 * @param corpusSize The number of documents in the corpus.
 * @param b The slope parameter of the tilting. Fixed at 0.003 for TW-IDF.
 */
def ewIle(entityWeight, avgReachableEntitiesFromSeeds, entityRelationCount, avgEntityRelationCount, entityCount, b=0.003) {
  entityWeight / (1 - b + b * entityRelationCount / avgEntityRelationCount) * Math.log((entityCount + 1) / avgReachableEntitiesFromSeeds)
}

//queryTokens = ['born', 'new', 'york']
//queryTokens = ['nirvana', 'members']
//offset = 0
//limit = 10

graph_of_entity_query: {
  query = g.withSack(0f).V().has("name", within(queryTokens))

  // Number of relations as an analogy to document lengths.
  entityRelationCountPipe = g.V()
    .has("type", "entity")
    .outE()
    .where(__.not(hasLabel("contained_in")))
    .inV()
    .groupCount()

  entityRelationCount = []

  entityRelationCountPipe.clone().fill(entityRelationCount)
  entityRelationCount = entityRelationCount[0]

  if (entityRelationCount.isEmpty()) return []

  avgEntityRelationCount = entityRelationCountPipe.clone()[0].values().sum() / entityRelationCountPipe.clone()[0].values().size()

  // Number of entities that have facts about them (we can later use a minimum number of facts).
  entityCount = g.V()
    .where(
      has("type", "entity")
      .and()
      .outE().where(__.not(hasLabel("contained_in")))
    )
    .dedup()
    .count()
    .next()

  seedScoresPipe = query.clone()
    .union(
      __.out("contained_in"),
      __.where(__.not(out("contained_in"))))
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

  distancesToSeedsPerEntity = seedScoresPipe.clone()
    .select(keys).as("seed")
    .repeat(both().where(neq("seed")))
    .times(maxDistance)
    .where(
      has("type", "entity")
      .and()
      .outE().where(__.not(hasLabel("contained_in"))) // same argument as entityCount
    )
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

  avgReachableEntitiesFromSeedsPipe = seedScoresPipe.clone()
    .select(keys)
    .group()
      .by()
      .by(
        repeat(both().simplePath())
        .until(
          or(
            has("type", "entity"),
            loops().is(eq(2))
          )
        )
        .dedup()
        .count()
      )
    .unfold()

  avgReachableEntitiesFromSeeds = avgReachableEntitiesFromSeedsPipe.clone().select(values).sum().next() /
    avgReachableEntitiesFromSeedsPipe.clone().select(values).count().next()

  ewIle = distancesToSeedsPerEntity.clone()
    .collect {
      docID = "http://en.wikipedia.org/wiki/${it.key.value("name").replace(" ", "_")}"
      //seedCount = it.value.size()
      coverage = it.value.size() / seedScores.size()

      // Iterate over each seed.
      weight = it.value.collect { s ->
        // Iterate over each path length for seed s.
        a = s.value.collect { v ->
          seedScores.get(s.key, 0f) * 1f / v
        }
        a.sum() / a.size()
      }
      entityWeight = coverage * weight.sum() / weight.size()
      score = ewIle(entityWeight, avgReachableEntitiesFromSeeds, entityRelationCount.get(it.key, 0), avgEntityRelationCount, entityCount, b=0.003)
        
      [docID: docID.toString(), score: score]
    }
    .sort { -it.score }
    .drop(offset)
    .take(limit)

  [[results: ewIle, numDocs: distancesToSeedsPerEntity.clone().count().next()]]
}
