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
import armyant.hgoe.structures.Result;
import armyant.hgoe.structures.ResultSet;
import com.esotericsoftware.kryo.Kryo;
import com.esotericsoftware.kryo.serializers.MapSerializer;
import grph.Grph;
import grph.algo.AllPaths;
import grph.in_memory.InMemoryGrph;
import grph.path.ArrayListPath;
import grph.path.Path;
import it.unimi.dsi.fastutil.ints.IntOpenHashSet;
import it.unimi.dsi.fastutil.ints.IntSet;
import it.unimi.dsi.util.XoRoShiRo128PlusRandom;
import org.ahocorasick.trie.Emit;
import org.ahocorasick.trie.Trie;
import org.apache.commons.collections4.BidiMap;
import org.apache.commons.collections4.bidimap.DualHashBidiMap;
import org.apache.commons.lang3.tuple.Pair;
import org.objenesis.strategy.StdInstantiatorStrategy;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import toools.collections.primitive.LucIntHashSet;
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
    private static final int MAX_PATHS_PER_PAIR = 1000;
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

        logger.info("Using in-memory version of Hypergraph of Entity for {}", path);

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

    private LucIntSet getQueryTermNodeIDs(List<String> terms) {
        LucIntSet termNodes = new LucIntHashSet();

        for (String term : terms) {
            TermNode termNode = new TermNode(term);
            if (nodeIndex.containsKey(termNode)) {
                termNodes.add(nodeIndex.get(termNode));
            }
        }

        return termNodes;
    }

    private LucIntSet getSeedNodeIDs(LucIntSet queryTermNodeIDs) {
        LucIntSet seedNodes = new LucIntHashSet();

        for (Integer queryTermNode : queryTermNodeIDs) {
            LucIntSet localSeedNodes = new LucIntHashSet();

            IntSet edgeIDs;
            if (graph.containsVertex(queryTermNode)) {
                edgeIDs = graph.getEdgesIncidentTo(queryTermNode);
            } else {
                edgeIDs = new IntOpenHashSet();
            }

            for (int edgeID : edgeIDs) {
                Edge edge = edgeIndex.getKey(edgeID);
                if (edge instanceof DocumentEdge)
                    continue; // for now ignore document co-occurrence relation to imitate GoE
                // XXX Not sure about this, since these hyperedges are directed.
                for (int nodeID : graph.getDirectedHyperEdgeTail(edgeID)) {
                    Node node = nodeIndex.getKey(nodeID);
                    if (node instanceof EntityNode) {
                        localSeedNodes.add(nodeID);
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

    /*private double coverage(EntityNode entityNode, Set<Node> seedNodes) {
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
    }*/

    // TODO Can be improved with an edge index per edge type: Map<Class<? extends Edge>, Set<Integer>>
    private LucIntSet getUndirectedNeighborsPerEdgeType(int sourceNodeID, Class edgeType) {
        LucIntSet result = new LucIntHashSet();
        result.addAll(graph.getEdgesIncidentTo(sourceNodeID).stream()
                .filter(edgeID -> {
                    Edge edge = edgeIndex.getKey(edgeID);
                    return edgeType.isInstance(edge);
                })
                .flatMap(edgeID -> {
                    LucIntSet nodeIDs = new LucIntHashSet();
                    nodeIDs.addAll(graph.getDirectedHyperEdgeHead(edgeID));
                    nodeIDs.addAll(graph.getDirectedHyperEdgeTail(edgeID));
                    return nodeIDs.stream().filter(nodeID -> !nodeID.equals(sourceNodeID));
                })
                .collect(Collectors.toSet()));
        return result;
    }

    private double confidenceWeight(int seedNodeID, LucIntSet queryTermNodeIDs) {
        Node seedNode = nodeIndex.getKey(seedNodeID);

        if (seedNode == null) return 0;

        if (seedNode instanceof TermNode) return 1;

        LucIntSet neighborIDs = getUndirectedNeighborsPerEdgeType(seedNodeID, ContainedInEdge.class);

        LucIntSet linkedQueryTermNodes = new LucIntHashSet();
        linkedQueryTermNodes.addAll(neighborIDs);
        linkedQueryTermNodes.retainAll(queryTermNodeIDs);

        //if (neighborIDs.isEmpty()) return 0;

        return (double) linkedQueryTermNodes.size() / neighborIDs.size();
    }

    public Map<Integer, Double> seedNodeConfidenceWeights(LucIntSet seedNodeIDs, LucIntSet queryTermNodeIDs) {
        Map<Integer, Double> weights = new HashMap<>();

        for (int seedNode : seedNodeIDs) {
            weights.put(seedNode, confidenceWeight(seedNode, queryTermNodeIDs));
        }

        return weights;
    }

    private double perSeedScoreDijkstra(int entityNodeID, int seedNodeID, double seedWeight) {
        double seedScore = 0d;
        Path shortestPath = graph.getShortestPath(entityNodeID, seedNodeID);
        if (shortestPath != null) seedScore = seedWeight * 1d / (1 + shortestPath.getLength());
        return seedScore;
    }

    private double perSeedScoreAllPaths(int entityNodeID, int seedNodeID, double seedWeight) {
        double seedScore = 0d;

        List<Path> paths = AllPaths.compute(entityNodeID, graph, SEARCH_MAX_DISTANCE, MAX_PATHS_PER_PAIR, false)
                .stream()
                .flatMap(Collection::stream)
                .filter(path -> path.containsVertex(seedNodeID))
                .collect(Collectors.toList());

        for (Path path : paths) {
            seedScore += seedWeight * 1d / (1 + path.getLength());
        }
        seedScore /= 1 + paths.size();

        return seedScore;
    }

    // TODO Should follow Bellaachia2013 for random walks on hypergraphs (Equation 14)
    private Integer getRandom(IntSet elementIDs) {
        return elementIDs.stream()
                .skip((int) (elementIDs.size() * RNG.nextDoubleFast()))
                .findFirst().get();
    }

    private Path randomWalk(int startNodeID, int length) {
        Path path = new ArrayListPath();
        path.extend(startNodeID);
        randomStep(startNodeID, length, path);
        return path;
    }

    private void randomStep(int nodeID, int remainingSteps, Path path) {
        if (remainingSteps == 0) return;

        IntSet edgeIDs = graph.getEdgesIncidentTo(nodeID);
        int randomEdgeID = getRandom(edgeIDs);

        IntSet nodeIDs = graph.getDirectedHyperEdgeTail(randomEdgeID);
        int randomNodeID = getRandom(nodeIDs);

        path.extend(randomEdgeID, randomNodeID);
        randomStep(randomNodeID, remainingSteps - 1, path);
    }

    // FIXME Unfinished
    private double perSeedScoreRandomWalk(int entityNodeID, int seedNodeID, double seedWeight) {
        double seedScore = 0d;
        for (int i = 0; i < WALK_ITERATIONS; i++) {
            Path randomPath = randomWalk(entityNodeID, WALK_LENGTH);
            int seedIndex = randomPath.indexOfVertex(seedNodeID);
            if (seedIndex != -1) seedScore += seedWeight * seedIndex;
        }
        return seedScore / 10;
    }

    public double perSeedScore(int entityNodeID, int seedNodeID, double seedWeight, PerSeedScoreMethod method) {
        logger.debug("Calculating score based on seed {} using {} method", seedNodeID, method);
        switch (method) {
            case ALL_PATHS:
                return perSeedScoreAllPaths(entityNodeID, seedNodeID, seedWeight);
            case DIJKSTA:
                return perSeedScoreDijkstra(entityNodeID, seedNodeID, seedWeight);
            case RANDOM_WALK:
                return perSeedScoreRandomWalk(entityNodeID, seedNodeID, seedWeight);
        }
        return 0;
    }

    public double entityWeight(int entityNodeID, Map<Integer, Double> seedNodeWeights) {
        double score = 0d;

        // Get all paths between the entity and a seed node (within a maximum distance; null by default).
        for (Map.Entry<Integer, Double> entry : seedNodeWeights.entrySet()) {
            int seedNodeID = entry.getKey();
            double seedWeight = entry.getValue();
            score += perSeedScore(entityNodeID, seedNodeID, seedWeight, PerSeedScoreMethod.RANDOM_WALK);
        }

        score = seedNodeWeights.isEmpty() ? 0 : score / seedNodeWeights.size();
        //score *= coverage(entityNode, seedNodeWeights.keySet());

        if (score > 0) System.out.println(score + "\t" + entityNodeID);

        return score;
    }

    /*private Set<Node> getNeighborhood(Node node, int depth) {
        return getNeighborhood(node, depth, new HashSet<>());
    }

    private Set<Node> getNeighborhood(Node node, int depth, Set<Node> visited) {
        visited.add(node);

        Set<Node> neighborhood = new HashSet<>();

        if (depth == 0) return neighborhood;

        Collection<Node> neighbors = graph.getUndirectedNeighborsPerEdgeType(node);
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

    private double jaccardSimilarity(LucIntSet a, LucIntSet b) {
        LucIntSet intersect = new LucIntHashSet();
        intersect.addAll(a);
        intersect.retainAll(b);

        LucIntSet union = new LucIntHashSet();
        union.addAll(a);
        union.addAll(b);

        return (double) intersect.size() / union.size();
    }

    public double jaccardScore(int entityNodeID, Map<Integer, Pair<LucIntSet, Double>> seedNeighborsWeights) {
        return seedNeighborsWeights.entrySet().stream().map(seed -> {
            LucIntSet seedNeighbors = seed.getValue().getLeft();
            LucIntSet entityNeighbors = graph.getNeighbours(entityNodeID);
            return seed.getValue().getRight() * jaccardSimilarity(seedNeighbors, entityNeighbors);
        }).mapToDouble(f -> f).sum();
    }

    private Set<String> getDocIDs(int entityNodeID) {
        return graph.getNeighbours(entityNodeID, Grph.DIRECTION.in).stream()
                .map(neighborID -> nodeIndex.getKey(neighborID))
                .filter(neighbor -> neighbor instanceof DocumentNode)
                .map(Node::getName)
                .collect(Collectors.toSet());
    }

    public ResultSet search(String query) throws IOException {
        return search(query, RankingFunction.JACCARD_SCORE);
    }

    public ResultSet search(String query, RankingFunction function) throws IOException {
        ResultSet resultSet = new ResultSet();

        List<String> tokens = analyze(query);
        LucIntSet queryTermNodeIDs = getQueryTermNodeIDs(tokens);

        LucIntSet seedNodeIDs = getSeedNodeIDs(queryTermNodeIDs);
        //System.out.println("Seed Nodes: " + seedNodeIDs.stream().map(nodeID -> nodeID + "=" + nodeIndex.getKey(nodeID).toString()).collect(Collectors.toList()));

        Map<Integer, Double> seedNodeWeights = seedNodeConfidenceWeights(seedNodeIDs, queryTermNodeIDs);
        //System.out.println("Seed Node Confidence Weights: " + seedNodeWeights);
        logger.info("{} seed nodes weights calculated for [ {} ]", seedNodeWeights.size(), query);

        Map<Integer, Pair<LucIntSet, Double>> seedNeighborsWeights = new HashMap<>();
        for (Map.Entry<Integer, Double> entry : seedNodeWeights.entrySet()) {
            seedNeighborsWeights.put(entry.getKey(), Pair.of(graph.getNeighbours(entry.getKey()), entry.getValue()));
        }

        graph.getVertices().parallelStream().forEach(nodeID -> {
            Node node = nodeIndex.getKey(nodeID);
            if (node instanceof EntityNode) {
                EntityNode entityNode = (EntityNode) node;
                logger.debug("Ranking {} using {}", entityNode, function);

                double score = 0d;
                switch (function) {
                    case ENTITY_WEIGHT:
                        score = entityWeight(nodeID, seedNodeWeights);
                        break;
                    case JACCARD_SCORE:
                        score = jaccardScore(nodeID, seedNeighborsWeights);
                }

                if (score > 0) {
                    synchronized (this) {
                        resultSet.addResult(new Result(score, entityNode, getDocIDs(nodeID)));
                    }
                }
            }
        });

        logger.info("{} entities ranked for [ {} ]", resultSet.getNumDocs(), query);

        return resultSet;
    }

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
        RANDOM_WALK
    }

    private enum RankingFunction {
        ENTITY_WEIGHT,
        JACCARD_SCORE
    }
}
