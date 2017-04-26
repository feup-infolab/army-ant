# Select a set of vertices and launch traversers from those. Enables correct path computation.
g.V(g.V().has("name", within(["born", "new", "york"])).as("q").union(__.out("contained_in"), __.where(__.not(out("contained_in")))).id().toList()).path().by("name")

# Provide two maps, one with the number of terms matching an entity and another with the degree of each entity node.
g.V().has("name", within(["born", "new", "york"])).as("q").out("contained_in").union(group().by().by(count()).as("c"), group().by().by(both().count()))

# Find poles (term and entity nodes) and return paths to other entity nodes (discard poles) within a maximum distance.
g.V().has("name", within(["born", "new", "york"])).as("q").union(__.out("contained_in"), __.where(__.not(out("contained_in")))).repeat(both().where(neq("q"))).times(1).where(has("type", "entity")).path().by("name")

# Example of a more complex sack() usage.
g.withSack(0f).V().has("name", within(["born", "new", "york"])).as("q").out("contained_in").as("e").group().by().by(sack(assign).by(count()).sack(sum).by(both().count()).sack())

