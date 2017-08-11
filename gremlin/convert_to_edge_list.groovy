convert_to_edge_list: {
  if (useNames) {
    g.V().as("v")
      .project("v", "n")
        .by(values("name"))
        .by(
          both()
            .where(neq("v"))
            .values("name")
        )
      .order()
        .by(select("v"))
  } else {
    g.V().as("v")
      .project("v", "n")
        .by()
        .by(
          both()
            .where(neq("v"))
        )
      .order()
        .by(select("v").id())
  }
}
