package armyant.hgoe.inmemory;

import armyant.hgoe.HypergraphOfEntity;
import armyant.hgoe.inmemory.edges.ContainedInEdge;
import armyant.hgoe.inmemory.edges.DocumentEdge;
import armyant.hgoe.inmemory.edges.Edge;
import armyant.hgoe.inmemory.edges.RelatedToEdge;
import armyant.hgoe.inmemory.nodes.DocumentNode;
import armyant.hgoe.inmemory.nodes.EntityNode;
import armyant.hgoe.inmemory.nodes.Node;
import armyant.hgoe.inmemory.nodes.TermNode;
import armyant.hgoe.inmemory.traversals.AllPaths;
import armyant.hgoe.structures.Document;
import armyant.hgoe.structures.Result;
import armyant.hgoe.structures.ResultSet;
import edu.uci.ics.jung.algorithms.shortestpath.BFSDistanceLabeler;
import edu.uci.ics.jung.graph.SetHypergraph;
import org.apache.commons.lang3.SerializationUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.FileInputStream;
import java.io.FileNotFoundException;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.*;
import java.util.stream.Collectors;

/**
 * Created by jldevezas on 2017-10-23.
 */
public class HypergraphOfEntityInMemory extends HypergraphOfEntity {
    private static final Logger logger = LoggerFactory.getLogger(HypergraphOfEntityInMemory.class);
    private static final Integer SEARCH_MAX_DISTANCE = 2;

    private String path;
    private SetHypergraph<Node, Edge> graph;

    private long counter;
    private long totalTime;
    private float avgTimePerDocument;

    public HypergraphOfEntityInMemory(String path) {
        this(path, false);
    }

    public HypergraphOfEntityInMemory(String path, boolean overwrite) {
        super();
        this.path = path;

        logger.info("Using in-memory version of Hypergraph of Entity");

        if (overwrite) {
            logger.info("Overwriting graph in {}, if it exists", path);
            this.graph = new SetHypergraph<>();
        } else {
            try {
                logger.info("Loading graph from {}", path);
                this.graph = SerializationUtils.deserialize(new FileInputStream(path));
            } catch (FileNotFoundException e) {
                logger.warn("Graph not found in {}, creating", path);
                this.graph = new SetHypergraph<>();
            }
        }
    }

    private Set<TermNode> indexDocument(Document document, Set<EntityNode> entityNodes) throws IOException {
        List<String> tokens = analyze(document.getText());
        if (tokens.isEmpty()) return new HashSet<>();

        Set<Node> nodes = new HashSet<>(entityNodes);

        DocumentNode documentNode = new DocumentNode(document.getDocID());
        if (!graph.containsVertex(documentNode)) graph.addVertex(documentNode);

        Set<TermNode> termNodes = tokens.stream().map(token -> {
            TermNode termNode = new TermNode(token);
            if (!graph.containsVertex(termNode)) graph.addVertex(termNode);
            return termNode;
        }).collect(Collectors.toSet());

        nodes.addAll(termNodes);

        DocumentEdge link = new DocumentEdge(document.getDocID());
        graph.addEdge(link, nodes);

        return termNodes;
    }

    private Set<EntityNode> indexEntities(Document document) {
        Map<EntityNode, Set<EntityNode>> edges = document.getTriples().stream()
                .collect(
                        Collectors.groupingBy(t -> new EntityNode(t.getSubject()),
                        Collectors.mapping(t -> new EntityNode(t.getObject()), Collectors.toSet())));

        Set<EntityNode> entityNodes = new HashSet<>();

        for (Map.Entry<EntityNode, Set<EntityNode>> entry : edges.entrySet()) {
            if (!graph.containsVertex(entry.getKey())) graph.addVertex(entry.getKey());
            entry.getValue().forEach(node -> {
                entityNodes.add(node);
                if (!graph.containsVertex(node)) graph.addVertex(node);
            });

            RelatedToEdge link = new RelatedToEdge();
            graph.addEdge(link, entityNodes);
        }

        return entityNodes;
    }

    private void linkTextAndKnowledge(Set<TermNode> termNodes, Set<EntityNode> entityNodes) {
        for (EntityNode entityNode : entityNodes) {
            Set<Node> nodes = new HashSet<>();
            nodes.add(entityNode);

            for (TermNode termNode : termNodes) {
                if (entityNode.getName().toLowerCase().matches(".*\\b" + termNode.getName().toLowerCase() + "\\b.*")) {
                    nodes.add(termNode);
                }
            }

            if (nodes.isEmpty()) continue;

            ContainedInEdge link = new ContainedInEdge();
            graph.addEdge(link, nodes);
        }
    }

    public void indexCorpus(Collection<Document> corpus) throws IOException {
        corpus.parallelStream().forEach(document -> {
            try {
                index(document);
            } catch (IOException e) {
                logger.warn("Error indexing document {}, skpping", document.getDocID(), e);
            }
        });
    }

    public void index(Document document) throws IOException {
        long startTime = System.currentTimeMillis();

        Set<EntityNode> entityHandles = indexEntities(document);
        Set<TermNode> termHandles = indexDocument(document, entityHandles);
        linkTextAndKnowledge(termHandles, entityHandles);

        long time = System.currentTimeMillis() - startTime;
        totalTime += time;

        counter++;
        avgTimePerDocument = counter > 1 ? (avgTimePerDocument * (counter - 1) + time) / counter : time;

        if (counter % 100 == 0) {
            logger.info(
                    "{} indexed documents in {} ({}/doc, {}docs/h)",
                    counter, formatMillis(totalTime), formatMillis(avgTimePerDocument),
                    counter * 3600000 / totalTime);
        }
    }

    public void close() {
        logger.info("Dumping graph to {}", path);
        try {
            SerializationUtils.serialize(graph, new FileOutputStream(path));
        } catch (FileNotFoundException e) {
            logger.error("Unable to dump graph to {}", path, e);
        }
    }


    private Set<TermNode> getQueryTermNodes(List<String> terms) {
        Set<TermNode> termNodes = new HashSet<>();

        for (String term : terms) {
            TermNode termNode = new TermNode(term);
            if (graph.containsVertex(termNode)) termNodes.add(termNode);
        }

        return termNodes;
    }

    private Set<Node> getSeedNodes(Set<TermNode> queryTermNodes) {
        Set<Node> seedNodes = new HashSet<>();

        for (TermNode queryTermNode : queryTermNodes) {
            Set<Node> localSeedNodes = new HashSet<>();

            Collection<Edge> edges = null;
            if (graph.containsVertex(queryTermNode)) {
                edges = graph.getIncidentEdges(queryTermNode);
            } else {
                edges = new HashSet<>();
            }

            for (Edge edge : edges) {
                for (Node node : graph.getIncidentVertices(edge)) {
                    if (node instanceof EntityNode) {
                        localSeedNodes.add(node);
                    }
                }
            }

            if (localSeedNodes.isEmpty()) {
                localSeedNodes.add(queryTermNode);
            }

            seedNodes.addAll(localSeedNodes);
        }

        return seedNodes;
    }

    private double coverage(EntityNode entityNode, Set<Node> seedNodes) {
        if (seedNodes.isEmpty()) return 0d;

        BFSDistanceLabeler<Node, Edge> bfsDistanceLabeler = new BFSDistanceLabeler<>();
        Set<Node> reachedSeedNodes = new HashSet<>();

        for (Node seedNode : seedNodes) {
            if (bfsDistanceLabeler.getDistance(graph ,seedNode) != -1) {
                reachedSeedNodes.add(seedNode);
            }
        }

        return (double) reachedSeedNodes.size() / seedNodes.size();
    }

    private Set<Node> getNeighbors(Node sourceNode, Class edgeType) {
        return graph.getNeighbors(sourceNode).stream()
                .filter(edgeType::isInstance)
                .collect(Collectors.toSet());
    }

    private double confidenceWeight(Node seedNode, Set<TermNode> queryTermNodes) {
        if (seedNode == null) return 0;

        if (seedNode instanceof TermNode) return 1;

        Set<Node> neighbors = getNeighbors(seedNode, ContainedInEdge.class);

        Set<Node> linkedQueryTermNodes = new HashSet<>(neighbors);
        linkedQueryTermNodes.retainAll(queryTermNodes);

        return (double) linkedQueryTermNodes.size() / neighbors.size();
    }

    public Map<Node, Double> seedNodeConfidenceWeights(Set<Node> seedNodes, Set<TermNode> queryTermNodes) {
        Map<Node, Double> weights = new HashMap<>();

        for (Node seedNode : seedNodes) {
            weights.put(seedNode, confidenceWeight(seedNode, queryTermNodes));
        }

        return weights;
    }

    public double entityWeight(EntityNode entityNode, Map<Node, Double> seedNodeWeights) {
        double score = 0d;

        // Get all paths between the entity and a seed node (within a maximum distance; null by default).
        for (Node seedNode : seedNodeWeights.keySet()) {
            logger.debug("Calculating score based on seed {}", seedNode);

            double seedScore = 0d;

            AllPaths allPaths = new AllPaths(graph, entityNode, seedNode, SEARCH_MAX_DISTANCE);
            allPaths.traverse();
            List<List<Edge>> paths = allPaths.getPaths();

            for (List<Edge> path : paths) {
                seedScore += seedNodeWeights.get(seedNode) * 1d / path.size();
            }
            seedScore = paths.isEmpty() ? 0 : seedScore / paths.size();

            score += seedScore;
        }

        score = seedNodeWeights.isEmpty() ? 0 : score / seedNodeWeights.size();

        return score * coverage(entityNode, seedNodeWeights.keySet());
    }

    public ResultSet search(String query) throws IOException {
        ResultSet resultSet = new ResultSet();

        List<String> tokens = analyze(query);
        Set<TermNode> queryTermNodeHandles = getQueryTermNodes(tokens);

        Set<Node> seedNodes = getSeedNodes(queryTermNodeHandles);
        System.out.println("Seed Nodes: " + seedNodes.stream().map(Node::toString).collect(Collectors.toList()));

        Map<Node, Double> seedNodeWeights = seedNodeConfidenceWeights(seedNodes, queryTermNodeHandles);
        System.out.println("Seed Node Confidence Weights: " + seedNodeWeights);

        for (Node node : graph.getVertices()) {
            if (node instanceof EntityNode) {
                EntityNode entityNode = (EntityNode) node;
                logger.debug("Ranking {}", entityNode);
                double score = entityWeight(entityNode, seedNodeWeights);
                if (score > 0) resultSet.addResult(new Result(entityNode, score));
                //System.out.println(((Node) graph.get(entityNodeHandle)).getName() + ": " + score);
            }
        }

        return resultSet;
    }


    /*public void printStatistics() {
        long numNodes = graph.count(typePlus(Node.class));
        long numEdges = graph.count(typePlus(Edge.class));

        System.out.println("Nodes: " + numNodes);
        System.out.println("Edges: " + numEdges);
    }

    public void printDepthFirst(String fromNodeName) {
        HGHandle termNode = graph.findOne(and(typePlus(Node.class), eq("name", fromNodeName)));

        HGDepthFirstTraversal traversal = new HGDepthFirstTraversal(termNode, new SimpleALGenerator(graph));

        while (traversal.hasNext()) {
            Pair<HGHandle, HGHandle> current = traversal.next();
            HGLink l = graph.get(current.getFirst());
            Node atom = graph.get(current.getSecond());
            System.out.println("Visiting node " + atom + " pointed to by " + l);
        }
    }

    public void printNodes() {
        HGSearchResult<HGHandle> rs = graph.find(or(type(TermNode.class), type(EntityNode.class)));

        try {
            while (rs.hasNext()) {
                HGHandle current = rs.next();
                Node node = graph.get(current);
                System.out.println(node.getName() + " - " + node.getClass().getSimpleName());
            }
        } finally {
            rs.close();
        }
    }

    public void printEdges() {
        HGSearchResult<HGHandle> rs = graph.find(typePlus(Edge.class));

        try {
            while (rs.hasNext()) {
                HGHandle current = rs.next();

                Edge edge = graph.get(current);

                List<Node> headNodes = new ArrayList<>();
                List<Node> tailNodes = new ArrayList<>();

                for (HGHandle handle : edge.getHead()) {
                    headNodes.add(graph.get(handle));
                }

                for (HGHandle handle : edge.getTail()) {
                    tailNodes.add(graph.get(handle));
                }

                String headMembers = String.join(", ", headNodes.stream()
                        .map(Node::toString)
                        .collect(Collectors.toList()));

                String tailMembers = String.join(", ", tailNodes.stream()
                        .map(Node::toString)
                        .collect(Collectors.toList()));

                System.out.println(String.format(
                        "%s -[%s]-> %s", headMembers, edge.getClass().getSimpleName(), tailMembers));
            }
        } finally {
            rs.close();
        }
    }*/
}
