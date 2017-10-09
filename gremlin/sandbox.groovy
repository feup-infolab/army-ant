# Select a set of vertices and launch traversers from those. Enables correct path computation.
g.V(g.V().has("name", within(["born", "new", "york"])).as("q").union(__.out("contained_in"), __.where(__.not(out("contained_in")))).id().toList()).path().by("name")

# Provide two maps, one with the number of terms matching an entity and another with the degree of each entity node.
g.V().has("name", within(["born", "new", "york"])).as("q").out("contained_in").union(group().by().by(count()).as("c"), group().by().by(both().count()))

# Find poles (term and entity nodes) and return paths to other entity nodes (discard poles) within a maximum distance.
g.V().has("name", within(["born", "new", "york"])).as("q").union(__.out("contained_in"), __.where(__.not(out("contained_in")))).repeat(both().where(neq("q"))).times(1).where(has("type", "entity")).path().by("name")

# Example of a more complex sack() usage.
g.withSack(0f).V().has("name", within(["born", "new", "york"])).as("q").out("contained_in").as("e").group().by().by(sack(assign).by(count()).sack(sum).by(both().count()).sack())

# Select nodes with a minimum of 3 facts.
g.V().has("type", "entity").where(__.outE().where(__.not(hasLabel("contained_in"))).inV().count().is(gt(3))).values("name")

# Select entity nodes with facts about them (the documents?).
g.V().has("type", "entity").where(__.outE().where(__.not(hasLabel("contained_in"))).inV()).values("name")

# Path between two nodes based on name matching, with a maximum distance of 2.
g.V().has("name", "William Rockefeller").repeat(outE().inV()).until(or(filter { it.get().value("name").contains("New York") }, loops().is(eq(2)))).path().by("name").by(label)

## Subgraph selection
# INEX 2009 combined ego networks
g.V().has("name", within("North Lincolnshire", "West Yorkshire", "Boston")).union(bothE(),both().as("n").bothE().where(otherV().where(eq("n")))).subgraph("sg").cap("sg").next()
# INEX 2009 combined extended ego networks (includes all edges from neighbors)
g.V().has("name", within("2004 Houston Texans season", "Symphonic black metal")).union(bothE(),both().bothE().subgraph("sg").cap("sg").next()

## Count edges of different types for graph-of-entity
# All
g.V().outE().count()
# Synonym
g.V().outE("synonym").count()
# Contained In
g.V().outE("contained_in").count()
# Before
g.V().outE("before").count()
# Relation
g.V().outE().where(__.not(hasLabel("contained_in").or().hasLabel("synonym").or().hasLabel("before"))).count()

# Update a property
g.V().outE().has("doc_id").property("doc_id", values("doc_id").map { it.get().tokenize("/")[-1].tokenize(".")[0] })

# Alternative to termEntityFrequency (work in progress)

tefAlternative: {
  query = g.withSack(0f).V().has("name", within(queryTokens))

  queryTermMentionDocIDs = query.clone()
    .inE("before")
    .values("doc_id")
    .dedup()
    .toList()

  entityTermFrequency = g.V()
    .has("type", "entity")
    .has("doc_id", within(queryTermMentionDocIDs))
    .project("entity", "term", "doc_id")
      .by()
      //.by(__.in("contained_in").both("before").has("name", within(queryTokens)))
      .by(optional(__.in("contained_in").both("before").where(has("name", within(queryTokens)))))
      .by(values("doc_id"))
    //.next()
}
