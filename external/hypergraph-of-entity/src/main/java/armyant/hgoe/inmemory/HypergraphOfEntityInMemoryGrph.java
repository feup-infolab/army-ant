package armyant.hgoe.inmemory;

import armyant.hgoe.HypergraphOfEntity;
import armyant.hgoe.exceptions.HypergraphException;
import armyant.hgoe.inmemory.edges.ContainedInEdge;
import armyant.hgoe.inmemory.edges.DocumentEdge;
import armyant.hgoe.inmemory.edges.Edge;
import armyant.hgoe.inmemory.edges.RelatedToEdge;
import armyant.hgoe.inmemory.nodes.DocumentNode;
import armyant.hgoe.inmemory.nodes.EntityNode;
import armyant.hgoe.inmemory.nodes.Node;
import armyant.hgoe.inmemory.nodes.TermNode;
import armyant.hgoe.structures.Document;
import com.esotericsoftware.kryo.Kryo;
import com.esotericsoftware.kryo.serializers.MapSerializer;
import grph.Grph;
import grph.in_memory.InMemoryGrph;
import it.unimi.dsi.util.XoRoShiRo128PlusRandom;
import org.ahocorasick.trie.Emit;
import org.ahocorasick.trie.Trie;
import org.apache.commons.collections4.BidiMap;
import org.apache.commons.collections4.bidimap.DualHashBidiMap;
import org.apache.commons.lang3.StringUtils;
import org.objenesis.strategy.StdInstantiatorStrategy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import toools.collections.primitive.LucIntSet;

import java.io.*;
import java.util.*;
import java.util.stream.Collectors;

/**
 * Created by jldevezas on 2017-10-23.
 */
public class HypergraphOfEntityInMemoryGrph extends HypergraphOfEntity {
    private static final Logger logger = LoggerFactory.getLogger(HypergraphOfEntityInMemoryGrph.class);
    private static final int SEARCH_MAX_DISTANCE = 2;
    private static final int WALK_LENGTH = 3;
    private static final int WALK_ITERATIONS = 10;
    private static final XoRoShiRo128PlusRandom RNG = new XoRoShiRo128PlusRandom();
    private static final Kryo kryo;
    private static final MapSerializer nodeEdgeIndexSerializer;

    static {
        kryo = new Kryo();
        kryo.setInstantiatorStrategy(new StdInstantiatorStrategy());

        nodeEdgeIndexSerializer = new MapSerializer();
        nodeEdgeIndexSerializer.setKeyClass(Node.class, kryo.getSerializer(Node.class));
        nodeEdgeIndexSerializer.setKeysCanBeNull(false);
        nodeEdgeIndexSerializer.setValueClass(Integer.class, kryo.getSerializer(Integer.class));

        kryo.register(HashMap.class, nodeEdgeIndexSerializer);
    }

    private File directory;
    private InMemoryGrph graph;
    private BidiMap<Node, Integer> nodeIndex;
    private BidiMap<Edge, Integer> edgeIndex;

    private long counter;
    private long totalTime;
    private float avgTimePerDocument;

    public HypergraphOfEntityInMemoryGrph(String path) throws HypergraphException {
        this(path, false);
    }

    public HypergraphOfEntityInMemoryGrph(String path, boolean overwrite) throws HypergraphException {
        super();

        this.directory = new File(path);
        if (directory.exists()) {
            if (!directory.isDirectory()) {
                throw new HypergraphException(String.format("%s is not a directory", path));
            }

            if (!directory.canWrite()) {
                throw new HypergraphException(String.format("%s is not writable", path));
            }
        } else {
            if (!directory.mkdirs()) {
                throw new HypergraphException(String.format("Could not create directory %s", path));
            }
        }

        this.nodeIndex = new DualHashBidiMap<>();
        this.edgeIndex = new DualHashBidiMap<>();

        logger.info("Using in-memory version of Hypergraph of Entity");

        if (overwrite) {
            logger.info("Overwriting graph in {}, if it exists", path);
            this.graph = new InMemoryGrph();
        } else {
            load();
        }
    }

    private synchronized int getOrCreateNode(Node node) {
        if (nodeIndex.containsKey(node)) return nodeIndex.get(node);
        int nodeID = graph.addVertex();
        nodeIndex.put(node, nodeID);
        return nodeID;
    }

    private synchronized int createEdge(Edge edge) {
        int edgeID = graph.getNextEdgeAvailable();
        graph.addDirectedHyperEdge(edgeID);
        edgeIndex.put(edge, edgeID);
        return edgeID;
    }

    private synchronized int getOrCreateEdge(Edge edge) {
        if (edgeIndex.containsKey(edge)) return edgeIndex.get(edge);
        return createEdge(edge);
    }

    private void addNodesToHyperEdgeHead(int edgeID, Set<Integer> nodeIDs) {
        for (Integer nodeID : nodeIDs) {
            synchronized (this) {
                graph.addToDirectedHyperEdgeHead(edgeID, nodeID);
            }
        }
    }

    private void addNodesToHyperEdgeTail(int edgeID, Set<Integer> nodeIDs) {
        for (Integer nodeID : nodeIDs) {
            synchronized (this) {
                graph.addToDirectedHyperEdgeTail(edgeID, nodeID);
            }
        }
    }

    private void indexDocument(Document document) throws IOException {
        DocumentEdge documentEdge = new DocumentEdge(document.getDocID());
        int edgeID = getOrCreateEdge(documentEdge);

        DocumentNode documentNode = new DocumentNode(document.getDocID());
        int sourceDocumentNodeID = getOrCreateNode(documentNode);
        synchronized (this) {
            graph.addToDirectedHyperEdgeHead(edgeID, sourceDocumentNodeID);
        }

        Set<Integer> targetEntityNodeIDs = indexEntities(document);
        addNodesToHyperEdgeTail(edgeID, targetEntityNodeIDs);

        List<String> tokens = analyze(document.getText());
        if (tokens.isEmpty()) return;

        Set<Integer> targetTermNodeIDs = tokens.stream().map(token -> {
            TermNode termNode = new TermNode(token);
            return getOrCreateNode(termNode);
        }).collect(Collectors.toSet());
        addNodesToHyperEdgeTail(edgeID, targetTermNodeIDs);
    }

    private Set<Integer> indexEntities(Document document) {
        Map<EntityNode, Set<EntityNode>> edges = document.getTriples().stream()
                .collect(Collectors.groupingBy(
                        t -> new EntityNode(t.getSubject()),
                        Collectors.mapping(t -> new EntityNode(t.getObject()), Collectors.toSet())));

        Set<Integer> nodes = new HashSet<>();

        for (Map.Entry<EntityNode, Set<EntityNode>> entry : edges.entrySet()) {
            int sourceEntityNodeID = getOrCreateNode(entry.getKey());
            nodes.add(sourceEntityNodeID);

            RelatedToEdge relatedToEdge = new RelatedToEdge();
            int edgeID = createEdge(relatedToEdge);
            synchronized (this) {
                graph.addToDirectedHyperEdgeHead(edgeID, sourceEntityNodeID);
            }

            for (EntityNode node : entry.getValue()) {
                int targetEntityNodeID = getOrCreateNode(node);
                synchronized (this) {
                    graph.addToDirectedHyperEdgeTail(edgeID, targetEntityNodeID);
                }
                nodes.add(targetEntityNodeID);
            }
        }

        return nodes;
    }

    public void linkTextAndKnowledge() {
        logger.info("Building trie from term nodes");
        Trie.TrieBuilder trieBuilder = Trie.builder()
                .ignoreOverlaps()
                .ignoreCase()
                .onlyWholeWords();

        for (int termNodeID : graph.getVertices()) {
            Node termNode = nodeIndex.getKey(termNodeID);
            if (termNode instanceof TermNode) {
                trieBuilder.addKeyword(termNode.getName());
            }
        }

        Trie trie = trieBuilder.build();

        logger.info("Creating links between entity nodes and term nodes using trie");
        for (int entityNodeID : graph.getVertices()) {
            Node entityNode = nodeIndex.getKey(entityNodeID);
            if (entityNode instanceof EntityNode) {
                Collection<Emit> emits = trie.parseText(entityNode.getName());
                Set<Integer> termNodes = emits.stream()
                        .map(e -> nodeIndex.get(new TermNode(e.getKeyword())))
                        .collect(Collectors.toSet());

                if (termNodes.isEmpty()) continue;

                ContainedInEdge containedInEdge = new ContainedInEdge();
                int edgeID = createEdge(containedInEdge);
                addNodesToHyperEdgeHead(edgeID, termNodes);
                graph.addToDirectedHyperEdgeTail(edgeID, entityNodeID);
            }
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

        indexDocument(document);

        long time = System.currentTimeMillis() - startTime;
        totalTime += time;

        counter++;
        avgTimePerDocument = counter > 1 ? (avgTimePerDocument * (counter - 1) + time) / counter : time;

        if (counter % 100 == 0) {
            logger.info(
                    "{} indexed documents in {} ({}/doc, {} docs/h)",
                    counter, formatMillis(totalTime), formatMillis(avgTimePerDocument),
                    counter * 3600000 / totalTime);
        }
    }

    public void save() {
        logger.info("Saving index to {}", directory.getAbsolutePath());

        File nodeIndexFile = new File(directory, "node-index.ser");
        try {
            ObjectOutputStream output = new ObjectOutputStream(new FileOutputStream(nodeIndexFile));
            output.writeObject(nodeIndex);
            output.close();
            /*Output output = new Output(new FileOutputStream(nodeIndexFile));
            kryo.writeObject(output, nodeIndex, nodeEdgeIndexSerializer);
            output.close();*/
        } catch (IOException e) {
            logger.error("Unable to dump hypergraph to {}", nodeIndexFile, e);
        }

        File edgeIndexFile = new File(directory, "edge-index.ser");
        try {
            ObjectOutputStream output = new ObjectOutputStream(new FileOutputStream(edgeIndexFile));
            output.writeObject(edgeIndex);
            output.close();
            /*Output output = new Output(new FileOutputStream(edgeIndexFile));
            kryo.writeObject(output, edgeIndex, nodeEdgeIndexSerializer);
            output.close();*/
        } catch (IOException e) {
            logger.error("Unable to dump hypergraph to {}", edgeIndexFile, e);
        }

        File hypergraphFile = new File(directory, "hypergraph.ser");
        try {
            ObjectOutputStream output = new ObjectOutputStream(new FileOutputStream(hypergraphFile));
            output.writeObject(graph);
            output.close();
            /*Output hypergraphOutput = new Output(new FileOutputStream(hypergraphFile));
            kryo.writeObject(hypergraphOutput, graph);
            hypergraphOutput.close();*/
        } catch (IOException e) {
            logger.error("Unable to dump hypergraph to {}", hypergraphFile, e);
        }
    }

    public void load() {
        logger.info("Loading index from {}", directory.getAbsolutePath());

        File nodeIndexFile = new File(directory, "node-index.ser");
        try {
            ObjectInputStream input = new ObjectInputStream(new FileInputStream(nodeIndexFile));
            this.nodeIndex = (BidiMap) input.readObject();
            input.close();
            /*Input input = new Input(new FileInputStream(nodeIndexFile));
            this.nodeIndex = kryo.readObject(input, HashMap.class, nodeEdgeIndexSerializer);
            input.close();*/
        } catch (ClassNotFoundException | IOException e) {
            logger.warn("Node index not found in {}, creating", directory);
            this.nodeIndex = new DualHashBidiMap<>();
        }

        File edgeIndexFile = new File(directory, "edge-index.ser");
        try {
            ObjectInputStream input = new ObjectInputStream(new FileInputStream(edgeIndexFile));
            this.edgeIndex = (BidiMap) input.readObject();
            input.close();
            /*Input input = new Input(new FileInputStream(edgeIndexFile));
            this.edgeIndex = kryo.readObject(input, HashMap.class, nodeEdgeIndexSerializer);
            input.close();*/
        } catch (ClassNotFoundException | IOException e) {
            logger.warn("Edge index not found in {}, creating", directory);
            this.edgeIndex = new DualHashBidiMap<>();
        }

        File hypergraphFile = new File(directory, "hypergraph.ser");
        try {
            ObjectInputStream input = new ObjectInputStream(new FileInputStream(hypergraphFile));
            this.graph = (InMemoryGrph) input.readObject();
            input.close();
            /*Input input = new Input(new FileInputStream(hypergraphFile));
            this.graph = kryo.readObject(input, InMemoryGrph.class);
            input.close();*/
        } catch (ClassNotFoundException | IOException e) {
            logger.warn("Hypergraph not found in {}, creating", directory);
            this.graph = new InMemoryGrph();
        }
    }

    /*private Set<Node> getQueryTermNodes(List<String> terms) {
        Set<Node> termNodes = new HashSet<>();

        for (String term : terms) {
            TermNode termNode = new TermNode(term);
            if (graph.containsVertex(termNode)) termNodes.add(termNode);
        }

        return termNodes;
    }

    private Set<Node> getSeedNodes(Set<Node> queryTermNodes) {
        Set<Node> seedNodes = new HashSet<>();

        for (Node queryTermNode : queryTermNodes) {
            Set<Node> localSeedNodes = new HashSet<>();

            Collection<Edge> edges;
            if (graph.containsVertex(queryTermNode)) {
                edges = graph.getIncidentEdges(queryTermNode);
            } else {
                edges = new HashSet<>();
            }

            for (Edge edge : edges) {
                if (edge instanceof DocumentEdge)
                    continue; // for now ignore document co-occurrence relation to imitate GoE
                for (Node node : graph.getIncidentVertices(edge)) {
                    if (node instanceof EntityNode) {
                        localSeedNodes.add(node);
                    }
                }
            }

            if (localSeedNodes.isEmpty() && graph.containsVertex(queryTermNode)) {
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
            bfsDistanceLabeler.labelDistances(graph, seedNode);
            if (bfsDistanceLabeler.getDistance(graph, seedNode) != -1) {
                reachedSeedNodes.add(seedNode);
            }
        }

        return (double) reachedSeedNodes.size() / seedNodes.size();
    }

    private Set<Node> getNeighborsPerEdgeType(Node sourceNode, Class edgeType) {
        return graph.getIncidentEdges(sourceNode).stream()
                .filter(edgeType::isInstance)
                .flatMap(edge -> graph.getIncidentVertices(edge).stream().filter(n -> !n.equals(sourceNode)))
                .collect(Collectors.toSet());
    }

    private double confidenceWeight(Node seedNode, Set<Node> queryTermNodes) {
        if (seedNode == null) return 0;

        if (seedNode instanceof TermNode) return 1;

        Set<Node> neighbors = getNeighborsPerEdgeType(seedNode, ContainedInEdge.class);

        Set<Node> linkedQueryTermNodes = new HashSet<>(neighbors);
        linkedQueryTermNodes.retainAll(queryTermNodes);

        return (double) linkedQueryTermNodes.size() / neighbors.size();
    }

    public Map<Node, Double> seedNodeConfidenceWeights(Set<Node> seedNodes, Set<Node> queryTermNodes) {
        Map<Node, Double> weights = new HashMap<>();

        for (Node seedNode : seedNodes) {
            weights.put(seedNode, confidenceWeight(seedNode, queryTermNodes));
        }

        return weights;
    }

    // FIXME Adapter needs revision to work
    private double perSeedScoreAStar(EntityNode entityNode, Node seedNode, double seedWeight) {
        double seedScore = 0d;
        SearchProblem searchProblem = GraphSearchProblem
                .startingFrom((Node) entityNode)
                .in(new JUNGHipsterHypergraphAdapter<>(graph))
                .takeCostsFromEdges()
                .build();

        int distance = Hipster.createAStar(searchProblem).search(seedNode).getOptimalPaths().size();
        seedScore = seedWeight * 1d / (1 + distance);
        return seedScore;
    }

    private double perSeedScoreDijkstra(EntityNode entityNode, Node seedNode, double seedWeight) {
        double seedScore = 0d;
        Number distance = dijkstraDistance.getDistance(entityNode, seedNode);
        if (distance != null) seedScore = seedWeight * 1d / (1 + distance.doubleValue());
        return seedScore;
    }

    private double perSeedScoreAllPaths(EntityNode entityNode, Node seedNode, double seedWeight) {
        double seedScore = 0d;

        AllPaths allPaths = new AllPaths(graph, entityNode, seedNode, SEARCH_MAX_DISTANCE);
        allPaths.traverse();
        List<List<Edge>> paths = allPaths.getPaths();

        for (List<Edge> path : paths) {
            seedScore += seedWeight * 1d / (1 + path.size());
        }
        seedScore /= 1 + paths.size();

        return seedScore;
    }

    // TODO Should follow Bellaachia2013 for random walks on hypergraphs (Equation 14)
    private <T> T getRandom(Collection<T> collection) {
        return collection.stream()
                .skip((int) (collection.size() * RNG.nextDoubleFast()))
                .findFirst().get();
    }

    private List<Edge> randomWalk(Node startNode, int length) {
        List<Edge> path = new ArrayList<>();
        randomStep(startNode, length, path);
        return path;
    }

    private void randomStep(Node node, int remainingSteps, List<Edge> path) {
        if (remainingSteps == 0) return;

        Collection<Edge> edges = graph.getIncidentEdges(node);
        Edge randomEdge = getRandom(edges);

        Collection<Node> nodes = graph.getIncidentVertices(randomEdge);
        Node randomNode = getRandom(nodes);

        path.add(randomEdge);
        randomStep(randomNode, remainingSteps - 1, path);
    }

    // FIXME Unfinished
    private double perSeedScoreRandomWalk(EntityNode entityNode, Node seedNode, double seedWeight) {
        double seedScore = 0d;
        for (int i = 0; i < WALK_ITERATIONS; i++) {
            List<Edge> randomPath = randomWalk(entityNode, WALK_LENGTH);
            int seedIndex = randomPath.indexOf(seedNode);
            if (seedIndex != -1) seedScore += randomPath.indexOf(seedNode);
        }
        return seedScore / 10;
    }

    public double perSeedScore(EntityNode entityNode, Node seedNode, double seedWeight, PerSeedScoreMethod method) {
        logger.debug("Calculating score based on seed {} using {} method", seedNode, method);
        switch (method) {
            case ALL_PATHS:
                return perSeedScoreAllPaths(entityNode, seedNode, seedWeight);
            case DIJKSTA:
                return perSeedScoreDijkstra(entityNode, seedNode, seedWeight);
            case A_STAR:
                return perSeedScoreAStar(entityNode, seedNode, seedWeight);
            case RANDOM_WALK:
                return perSeedScoreRandomWalk(entityNode, seedNode, seedWeight);
        }
        return 0;
    }

    public double entityWeight(EntityNode entityNode, Map<Node, Double> seedNodeWeights) {
        double score = 0d;

        // Get all paths between the entity and a seed node (within a maximum distance; null by default).
        for (Map.Entry<Node, Double> entry : seedNodeWeights.entrySet()) {
            Node seedNode = entry.getKey();
            Double seedWeight = entry.getValue();
            score += perSeedScore(entityNode, seedNode, seedWeight, PerSeedScoreMethod.RANDOM_WALK);
        }

        score = seedNodeWeights.isEmpty() ? 0 : score / seedNodeWeights.size();
        //score *= coverage(entityNode, seedNodeWeights.keySet());

        if (score > 0) System.out.println(score + "\t" + entityNode);

        return score;
    }*/

    /*private Set<Node> getNeighborhood(Node node, int depth) {
        return getNeighborhood(node, depth, new HashSet<>());
    }

    private Set<Node> getNeighborhood(Node node, int depth, Set<Node> visited) {
        visited.add(node);

        Set<Node> neighborhood = new HashSet<>();

        if (depth == 0) return neighborhood;

        Collection<Node> neighbors = graph.getNeighborsPerEdgeType(node);
        neighborhood.addAll(neighbors);

        for (Node neighbor : neighbors) {
            if (visited.contains(neighbor)) continue;
            neighborhood.addAll(getNeighborhood(neighbor, depth - 1, visited));
        }

        return neighborhood;
    }*/

    /*public void updateQuerySubgraph(Set<Node> queryTermNodes) {
        logger.info("Updating query subgraph");
        Set<Node> nodes = new HashSet<>();
        for (Node queryTermNode : queryTermNodes) {
            nodes.addAll(getNeighborhood(queryTermNode, 0));
        }
        System.out.println(this.graph.getVertexCount() + " : " + this.graph.getEdgeCount());
        this.graph = FilterUtils.createInducedSubgraph(nodes, graph);
        System.out.println(this.graph.getVertexCount() + " : " + this.graph.getEdgeCount());
    }*/

    /*private <T> double jaccardSimilarity(Set<T> a, Set<T> b) {
        Set<T> intersect = new HashSet<>(a);
        a.retainAll(b);

        Set<T> union = new HashSet<>(a);
        union.addAll(b);

        return (double) intersect.size() / union.size();
    }

    public double jaccardScore(EntityNode entityNode, Map<Node, Pair<Set<Node>, Double>> seedNeighborsWeights) {
        double score = 0d;

        for (Map.Entry<Node, Pair<Set<Node>, Double>> seed : seedNeighborsWeights.entrySet()) {
            Set<Node> seedNeighbors = seed.getValue().getLeft();
            Set<Node> entityNeighbors = new HashSet<>(graph.getNeighbors(entityNode));
            score += seed.getValue().getRight() * jaccardSimilarity(seedNeighbors, entityNeighbors);
        }

        return score;
    }

    public ResultSet search(String query) throws IOException {
        return search(query, RankingFunction.JACCARD_SCORE);
    }

    public ResultSet search(String query, RankingFunction function) throws IOException {
        ResultSet resultSet = new ResultSet();

        List<String> tokens = analyze(query);
        Set<Node> queryTermNodes = getQueryTermNodes(tokens);

        Set<Node> seedNodes = getSeedNodes(queryTermNodes);
        System.out.println("Seed Nodes: " + seedNodes.stream().map(Node::toString).collect(Collectors.toList()));

        Map<Node, Double> seedNodeWeights = seedNodeConfidenceWeights(seedNodes, queryTermNodes);
        System.out.println("Seed Node Confidence Weights: " + seedNodeWeights);

        Map<Node, Pair<Set<Node>, Double>> seedNeighborsWeights = new HashMap<>();
        for (Map.Entry<Node, Double> entry : seedNodeWeights.entrySet()) {
            seedNeighborsWeights.put(entry.getKey(), Pair.of(new HashSet<>(graph.getNeighbors(entry.getKey())), entry.getValue()));
        }

        for (Node node : graph.getVertices()) {
            if (node instanceof EntityNode) {
                EntityNode entityNode = (EntityNode) node;
                logger.debug("Ranking {} using {}", entityNode, function);

                double score = 0d;
                switch (function) {
                    case ENTITY_WEIGHT:
                        score = entityWeight(entityNode, seedNodeWeights);
                        break;
                    case JACCARD_SCORE:
                        score = jaccardScore(entityNode, seedNeighborsWeights);
                }

                if (score > 0) resultSet.addResult(new Result(entityNode, score));
            }
        }

        return resultSet;
    }*/

    public void printStatistics() {
        long numNodes = graph.getNumberOfVertices();
        long numEdges = graph.getNumberOfEdges();

        System.out.println("Nodes: " + numNodes);
        System.out.println("Edges: " + numEdges);
    }

    public void printNodes() {
        for (int nodeID : graph.getVertices()) {
            Node node = nodeIndex.getKey(nodeID);
            System.out.println(String.format("%d\t%s - %s", nodeID, node.getName(), node.getClass().getSimpleName()));
        }
    }

    /*public void printDepthFirst(String fromNodeName) {
        HGHandle termNode = graph.findOne(and(typePlus(Node.class), eq("name", fromNodeName)));

        HGDepthFirstTraversal traversal = new HGDepthFirstTraversal(termNode, new SimpleALGenerator(graph));

        while (traversal.hasNext()) {
            Pair<HGHandle, HGHandle> current = traversal.next();
            HGLink l = graph.get(current.getFirst());
            Node atom = graph.get(current.getSecond());
            System.out.println("Visiting node " + atom + " pointed to by " + l);
        }
    }*/

    public void printEdges() {
        for (int edgeID : graph.getEdges()) {
            LucIntSet head = graph.getDirectedHyperEdgeHead(edgeID);
            LucIntSet tail = graph.getDirectedHyperEdgeTail(edgeID);
            Edge edge = edgeIndex.getKey(edgeID);
            System.out.println(String.format(
                    "%d\t[%s] %s -> %s", edgeID, edge.getClass().getSimpleName(), head, tail));
        }
    }

    private enum PerSeedScoreMethod {
        DIJKSTA,
        ALL_PATHS,
        RANDOM_WALK,
        A_STAR
    }

    private enum RankingFunction {
        ENTITY_WEIGHT,
        JACCARD_SCORE
    }
}
