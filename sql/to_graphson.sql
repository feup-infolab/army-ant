--WITH edges AS (SELECT * FROM edges LIMIT 100)
SELECT node_id, nodes.label AS label, nodes.attributes AS properties, out_e, in_e
FROM (
  SELECT node_id, (array_agg(target_nodes))[1] AS out_e, (array_agg(source_nodes))[1] AS in_e
  FROM (
    (
      SELECT source_node_id AS node_id, json_build_object(
        label, json_agg(json_build_object(
          'id', edge_id,
          'inV', target_node_id,
          'properties', attributes))) AS target_nodes
      FROM edges
      GROUP BY label, node_id
    ) outE
    FULL JOIN (
      SELECT target_node_id AS node_id, json_build_object(
        label, json_agg(json_build_object(
          'id', edge_id,
          'outV', source_node_id,
          'properties', attributes))) AS source_nodes
      FROM edges
      GROUP BY label, node_id
    ) inE
    USING (node_id)
  ) graphson_nodes
  GROUP BY node_id
) graphson_labeled_nodes
JOIN nodes USING (node_id)
