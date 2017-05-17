/**
 * Calculate the EW-ILF, from Graph of Entity model, for an entity node linked to a seed node.
 * EW-ILF stands for Entity Weight - Inverse Link Frequency
 *
 * @param entityWeight Entity weight, based on seed coverage, distance to seeds and seed weight.
 * @param avgReachableEntitiesFromSeeds Average number of entity nodes with an undirected path of maximum length 2 to a seed node (analogy: DF).
 * @param entityRelationCount The number of relations to other entities (analogy: document length).
 * @param avgEntityRelationCount The average number of relations between a pair of entities in the graph (analogy: avg. document length).
 * @param entityCount The number of entities in the graph (analogy: corpus size).
 * @param b The slope parameter of the tilting. Using 0.003, like TW-IDF (should be tuned).
 */
def ewIlf(entityWeight, avgReachableEntitiesFromSeeds, entityRelationCount, avgEntityRelationCount, entityCount, b=0.003) {
  //entityWeight / (1 - b + b * entityRelationCount / avgEntityRelationCount) * Math.log((entityCount + 1) / avgReachableEntitiesFromSeeds)
  //entityWeight / (1 - b + b * entityRelationCount / avgEntityRelationCount) * entityCount / avgReachableEntitiesFromSeeds
  entityWeight
}

//queryTokens = ['born', 'new', 'york']
//queryTokens = ['born']
//queryTokens = ['musician', 'architect']
//offset = 0
//limit = 5

graph_of_entity_query: {
  query = g.withSack(0f).V().has("name", within(queryTokens))

  if (query.clone().count().next() < 1) return [[results: [:], numDocs: 0]]

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

  entityTermFrequency = g.V().outE("before")
    .dedup()
    .where(inV().has("name", within(queryTokens)))
    .project("entity", "term")
      .by { p = g.V().has("url", it.value("doc_id")); if (p.hasNext()) return p.next() else return none }
      .by(inV())
    .where(__.not(select("entity").is(none)))
    .group()
      .by(select("entity"))
      .by(count())
    .unfold()
    .collectEntries { [(it.key): (1 + Math.log(it.value))] }

  //return entityTermFrequency

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

  maxDistance = 1

  // shortest path
  distancesToSeedsPerEntity = seedScoresPipe.clone()
    .select(keys).as("seed")
    .repeat(both().simplePath().where(neq("seed")))
    .until(
      has("type", "entity")
      .and()
      .outE().where(__.not(hasLabel("contained_in"))) // same argument as entityCount
      .or()
      .loops().is(eq(maxDistance))
    )
    .where(
      __.has("type", "entity")
      .and()
      .outE().where(__.not(hasLabel("contained_in"))) // same argument as entityCount
    )
    .path().as("path")
    .project("entity", "seed", "distance")
      .by { it.getAt(it.size() - 1) }
      .by { it.getAt(2) }
      .by(sack(assign).by(count(local)).sack(sum).by(constant(-2)).sack())
    .group()
      .by(select("entity"))
      .by(group().by(select("seed")).by(select("distance").min()))
    .unfold()

  //return distancesToSeedsPerEntity

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

  ewIlf = distancesToSeedsPerEntity.clone().collect {
      docID = "http://en.wikipedia.org/wiki/${it.key.value("name").replace(" ", "_")}"
      coverage = it.value.size() / seedScores.size()

      // Iterate over each seed.
      weight = it.value.collect { s ->
        seedScores.get(s.key, 0f) * 1f / s.value
      }
      avgWeightedInversePathLength = weight.sum() / weight.size()
      entityWeight = coverage * avgWeightedInversePathLength
      b = 0.003
      //score = ewIlf(entityWeight, avgReachableEntitiesFromSeeds, entityRelationCount.get(it.key, 0), avgEntityRelationCount, entityCount, b=b)
      score = 0.7 * entityWeight + 0.3 * entityTermFrequency.get(it.key, 0)
        
      [
        docID: docID.toString(),
        score: score,
        components: [[
          docID: docID.toString(),
          'c(e, S)': coverage.doubleValue(),
          'w(e)': avgWeightedInversePathLength,
          'wNorm(e, E)': (1 - b + b * entityRelationCount.get(it.key, 0) / avgEntityRelationCount).doubleValue(),
          'ew(e, E, b)': (entityWeight / (1 - b + b * entityRelationCount.get(it.key, 0) / avgEntityRelationCount)).doubleValue(),
          'etf(t, e)': entityTermFrequency.get(it.key, 0)
          //'|E|': entityCount,
          //'avgle': avgReachableEntitiesFromSeeds.doubleValue(),
          //'ilf(E)': Math.log((entityCount + 1) / avgReachableEntitiesFromSeeds).doubleValue(),
          //'ewIlf(e, E, Se, S)': score
        ]]
      ]
    }
    .plus(entityTermFrequency.collect {
      docID = "http://en.wikipedia.org/wiki/${it.key.value("name").replace(" ", "_")}"

      score = 0.1 * it.value

      [
        docID: docID.toString(),
        score: score.doubleValue(),
        components: [[
          docID: docID.toString(),
          'c(e, S)': 0d,
          'w(e)': 0d,
          'wNorm(e, E)': 0d,
          'ew(e, E, b)': 0d,
          'etf(t, e)': it.value.doubleValue()
        ]]
      ]
    })
    .unique { a, b -> a.docID <=> b.docID }
    .sort { -it.score }

  numDocs = ewIlf.size()
  ewIlf = ewIlf
    .drop(offset)
    .take(limit)

  [[results: ewIlf, numDocs: numDocs]]
}
