package armyant.hgoe.inmemory;

import armyant.Engine;
import armyant.hgoe.exceptions.HypergraphException;
import armyant.hgoe.inmemory.edges.*;
import armyant.hgoe.inmemory.nodes.DocumentNode;
import armyant.hgoe.inmemory.nodes.EntityNode;
import armyant.hgoe.inmemory.nodes.Node;
import armyant.hgoe.inmemory.nodes.TermNode;
import armyant.structures.*;
import armyant.structures.yaml.PruneConfig;
import edu.mit.jwi.IRAMDictionary;
import edu.mit.jwi.RAMDictionary;
import edu.mit.jwi.data.ILoadPolicy;
import edu.mit.jwi.item.*;
import grph.algo.AllPaths;
import grph.algo.ConnectedComponentsAlgorithm;
import grph.in_memory.InMemoryGrph;
import grph.io.ParseException;
import grph.path.ArrayListPath;
import grph.properties.NumericalProperty;
import grph.properties.ObjectProperty;
import it.unimi.dsi.fastutil.floats.FloatArrayList;
import it.unimi.dsi.fastutil.floats.FloatList;
import it.unimi.dsi.fastutil.ints.*;
import org.ahocorasick.trie.Emit;
import org.ahocorasick.trie.Trie;
import org.apache.commons.collections4.BidiMap;
import org.apache.commons.collections4.bidimap.DualHashBidiMap;
import org.apache.commons.lang3.ArrayUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.tuple.Pair;
import org.apache.commons.math3.analysis.function.Sigmoid;
import org.apache.tinkerpop.gremlin.structure.Direction;
import org.apache.tinkerpop.gremlin.structure.Vertex;
import org.apache.tinkerpop.gremlin.structure.io.IoCore;
import org.apache.tinkerpop.gremlin.tinkergraph.structure.TinkerGraph;
import org.apache.tinkerpop.gremlin.util.iterator.IteratorUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xml.sax.SAXException;
import toools.collections.primitive.LucIntHashSet;

import javax.xml.parsers.ParserConfigurationException;
import java.io.*;
import java.nio.file.Paths;
import java.util.*;
import java.util.stream.Collectors;
import java.util.zip.GZIPInputStream;

/**
 * Created by jldevezas on 2017-10-23.
 */
// TODO instaceof might be replaced by a Grph Property of some sort (is it faster?)
public class HypergraphOfEntityInMemory extends Engine {
    private static final Logger logger = LoggerFactory.getLogger(HypergraphOfEntityInMemory.class);
    private static final Sigmoid sigmoid = new Sigmoid();

    private static final int SEARCH_MAX_DISTANCE = 2;
    private static final int MAX_PATHS_PER_PAIR = 1000;

    private static final float DEFAULT_DOCUMENT_NODE_WEIGHT = 1;
    private static final float DEFAULT_DOCUMENT_EDGE_WEIGHT = 0.5f;

    private static final int DEFAULT_WALK_LENGTH = 3;
    private static final int DEFAULT_WALK_REPEATS = 1000;

    private static final float PROBABILITY_THRESHOLD = 0.005f;

    private static final String CONTEXT_FEATURES_FILENAME = "word2vec_simnet.graphml.gz";

    private List<Feature> features;
    private String featuresPath;
    private File directory;
    private InMemoryGrph graph;
    private NumericalProperty nodeWeights;
    private NumericalProperty edgeWeights;
    private ObjectProperty auxProperties;
    private BidiMap<Node, Integer> nodeIndex;
    private BidiMap<Edge, Integer> edgeIndex;
    private Map<Integer, IntSet> reachabilityIndex;
    private Trace trace;

    private long counter;
    private long totalTime;
    private float avgTimePerDocument;

    private int numDocs;

    public HypergraphOfEntityInMemory(String path) throws HypergraphException {
        this(path, new ArrayList<>());
    }

    public HypergraphOfEntityInMemory(String path, List<Feature> features) throws HypergraphException {
        this(path, features, null, false);
    }

    public HypergraphOfEntityInMemory(String path, List<Feature> features, String featuresPath) throws HypergraphException {
        this(path, features, featuresPath, false);
    }

    public HypergraphOfEntityInMemory(String path, List<Feature> features, String featuresPath, boolean overwrite) throws HypergraphException {
        super();

        this.features = features;
        this.featuresPath = featuresPath;

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

        this.graph = new InMemoryGrph();
        this.nodeWeights = new NumericalProperty("weight");
        this.edgeWeights = new NumericalProperty("weight");
        this.nodeIndex = new DualHashBidiMap<>();
        this.edgeIndex = new DualHashBidiMap<>();
        this.reachabilityIndex = new HashMap<>();
        this.trace = new Trace();

        logger.info("Using in-memory version of Hypergraph of Entity for {}", path);

        if (overwrite) {
            logger.info("Overwriting graph in {}, if it exists", path);
        } else {
            if (!load()) {
                logger.warn("Could not load graph in {}, creating", path);
            }
        }
    }

    public boolean hasFeature(Feature feature) {
        return features.contains(feature);
    }

    private synchronized int getOrCreateNode(Node node) {
        if (nodeIndex.containsKey(node)) return nodeIndex.get(node);
        int nodeID = graph.addVertex();
        nodeIndex.put(node, nodeID);
        return nodeID;
    }

    private synchronized int createDirectedEdge(Edge edge) {
        return createEdge(edge, true);
    }

    private synchronized int createUndirectedEdge(Edge edge) {
        return createEdge(edge, false);
    }

    private synchronized int createEdge(Edge edge, boolean directed) {
        int edgeID = graph.getNextEdgeAvailable();
        if (directed) {
            graph.addDirectedHyperEdge(edgeID);
        } else {
            graph.addUndirectedHyperEdge(edgeID);
        }
        edgeIndex.put(edge, edgeID);
        return edgeID;
    }

    private synchronized int getOrCreateDirectedEdge(Edge edge) {
        return getOrCreateEdge(edge, true);
    }

    private synchronized int getOrCreateUndirectedEdge(Edge edge) {
        return getOrCreateEdge(edge, false);
    }

    private synchronized int getOrCreateEdge(Edge edge, boolean directed) {
        if (edgeIndex.containsKey(edge)) return edgeIndex.get(edge);
        return createEdge(edge, directed);
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

    private void addNodesToUndirectedHyperEdge(int edgeID, Set<Integer> nodeIDs) {
        for (Integer nodeID : nodeIDs) {
            synchronized (this) {
                graph.addToUndirectedHyperEdge(edgeID, nodeID);
            }
        }
    }

    private void indexDocument(Document document) throws IOException {
        DocumentEdge documentEdge = new DocumentEdge(document.getDocID());
        int edgeID = getOrCreateUndirectedEdge(documentEdge);

        DocumentNode documentNode = new DocumentNode(document.getDocID());
        int sourceDocumentNodeID = getOrCreateNode(documentNode);
        synchronized (this) {
            graph.addToUndirectedHyperEdge(edgeID, sourceDocumentNodeID);
        }

        Set<Integer> targetEntityNodeIDs = indexEntities(document);
        addNodesToUndirectedHyperEdge(edgeID, targetEntityNodeIDs);

        List<String> tokens = analyze(document.getText());
        if (tokens.isEmpty()) return;

        Set<Integer> targetTermNodeIDs = tokens.stream().map(token -> {
            TermNode termNode = new TermNode(token);
            return getOrCreateNode(termNode);
        }).collect(Collectors.toSet());
        addNodesToUndirectedHyperEdge(edgeID, targetTermNodeIDs);

        numDocs++;
    }

    private Set<Integer> indexEntities(Document document) {
        Set<Node> nodes = new HashSet<>();

        for (Triple triple : document.getTriples()) {
            nodes.add(new EntityNode(document, triple.getSubject()));
            nodes.add(new EntityNode(document, triple.getObject()));
        }

        Set<Integer> nodeIDs = new HashSet<>();

        RelatedToEdge relatedToEdge = new RelatedToEdge();
        int edgeID = createUndirectedEdge(relatedToEdge);

        for (Node node : nodes) {
            int entityNodeID = getOrCreateNode(node);
            nodeIDs.add(entityNodeID);
            synchronized (this) {
                graph.addToUndirectedHyperEdge(edgeID, entityNodeID);
            }
        }

        return nodeIDs;
    }

    private void linkTextAndKnowledge() {
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
                int edgeID = createDirectedEdge(containedInEdge);
                addNodesToHyperEdgeTail(edgeID, termNodes);
                graph.addToDirectedHyperEdgeHead(edgeID, entityNodeID);
            }
        }
    }

    private void linkSynonyms() {
        logger.info("Creating links between synonyms ({synonyms})");
        IRAMDictionary dict = null;
        try {
            dict = new RAMDictionary(new File("/usr/share/wordnet"), ILoadPolicy.NO_LOAD);
            dict.open();

            for (int nodeID : graph.getVertices()) {
                Node node = nodeIndex.getKey(nodeID);
                if (node instanceof TermNode) {
                    IIndexWord idxWord = dict.getIndexWord(node.getName(), POS.NOUN);
                    if (idxWord != null) {
                        auxProperties.setValue(nodeID, idxWord.getTagSenseCount());
                        IWordID wordID = idxWord.getWordIDs().get(0);
                        IWord word = dict.getWord(wordID);
                        ISynset synset = word.getSynset();

                        for (IWord w : synset.getWords()) {
                            Set<String> syns = new HashSet<>(Arrays.asList(w.getLemma().toLowerCase().split("_")));
                            if (syns.size() > 1) {
                                SynonymEdge synonymEdge = new SynonymEdge();
                                int edgeID = createUndirectedEdge(synonymEdge);
                                graph.addToUndirectedHyperEdge(edgeID, nodeIndex.get(node));
                                for (String syn : syns) {
                                    Node synNode = new TermNode(syn);
                                    int synNodeID = getOrCreateNode(synNode);
                                    graph.addToUndirectedHyperEdge(edgeID, synNodeID);
                                }
                            }
                        }
                    }
                }
            }
        } catch (IOException e) {
            logger.error(e.getMessage(), e);
        } finally {
            if (dict != null) {
                dict.close();
            }
        }
    }

    private void linkContextuallySimilarTerms() throws IOException, ParseException, ParserConfigurationException, SAXException {
        logger.info("Creating links between terms that are contextually similar ({terms})");

        File simnetFile = Paths.get(featuresPath, CONTEXT_FEATURES_FILENAME).toFile();
        File uncompressedSimnetFile = File.createTempFile("army_ant-word2vec_simnet-", ".graphml");
        uncompressedSimnetFile.deleteOnExit();

        try (GZIPInputStream input = new GZIPInputStream(new FileInputStream(simnetFile));
             FileOutputStream output = new FileOutputStream(uncompressedSimnetFile)) {
            byte[] buffer = new byte[4096];
            int length;
            while ((length = input.read(buffer)) > 0) {
                output.write(buffer, 0, length);
            }
        }

        logger.info("Loading word2vec simnet");
        TinkerGraph simnet = TinkerGraph.open();
        simnet.io(IoCore.graphml()).readGraph(uncompressedSimnetFile.toString());

        simnet.vertices().forEachRemaining(v -> {
            if (IteratorUtils.count(v.edges(Direction.BOTH, "edge")) < 1) return;

            String term = (String) v.property("name").value();
            Node termNode = new TermNode(term);

            FloatList synSims = new FloatArrayList();
            if (nodeIndex.containsKey(termNode)) {
                ContextEdge contextEdge = new ContextEdge();
                int edgeID = createUndirectedEdge(contextEdge);
                this.graph.addToUndirectedHyperEdge(edgeID, nodeIndex.get(termNode));

                v.edges(Direction.BOTH, "edge").forEachRemaining(e -> {
                    Vertex source = e.bothVertices().next();
                    Vertex target = e.bothVertices().next();
                    Vertex other = source.property("name").value().equals(term) ? target : source;
                    Node otherNode = new TermNode((String) other.property("name").value());
                    if (nodeIndex.containsKey(otherNode)) {
                        this.graph.addToUndirectedHyperEdge(edgeID, nodeIndex.get(otherNode));
                    }

                    float weight = 1f;
                    if (e.property("weight").isPresent()) {
                        weight = (float) e.property("weight").value();
                    }
                    synSims.add(weight);
                });
                auxProperties.setValue(edgeID, synSims);
            }
        });
    }

    private float probalisticIDF(int numDocs, int numDocsWithTerm) {
        float probIDF = (float) Math.log10((float) (numDocs - numDocsWithTerm) / numDocsWithTerm);
        return Math.min(1, Math.max(0, probIDF));
    }

    private float linearIDF(int numDocs, int numDocsWithTerm) {
        return 1 - (float) numDocsWithTerm / numDocs;
    }

    private float sigmoidIDF(int numDocs, int numDocsWithTerm) {
        return sigmoidIDF(numDocs, numDocsWithTerm, 0.5f);
    }

    private float sigmoidIDF(int numDocs, int numDocsWithTerm, float alpha) {
        return (float) (2 * sigmoid.value(alpha * (numDocs - numDocsWithTerm) / numDocsWithTerm) - 1);
    }

    private void computeNodeWeights() {
        logger.info("Computing node weights");
        for (int nodeID : graph.getVertices()) {
            Node node = nodeIndex.getKey(nodeID);
            if (node instanceof DocumentNode) {
                nodeWeights.setValue(nodeID, DEFAULT_DOCUMENT_NODE_WEIGHT);
            } else if (node instanceof TermNode || node instanceof EntityNode) {
                int numDocsWithTerm = 0;
                for (int edgeID : graph.getEdgesIncidentTo(nodeID)) {
                    Edge edge = edgeIndex.getKey(edgeID);
                    if (edge instanceof DocumentEdge) {
                        numDocsWithTerm++;
                    }
                }
                nodeWeights.setValue(nodeID, sigmoidIDF(
                        numDocs, numDocsWithTerm, node instanceof TermNode ? 0.25f : 0.15f));
            }
        }
    }

    private float computeContainedInHyperEdgeWeight(int edgeID) {
        return 1f / graph.getDirectedHyperEdgeTail(edgeID).size();
    }

    private float computeRelatedToHyperEdgeWeight(int edgeID) {
        IntSet entityNodeIDs = graph.getUndirectedHyperEdgeVertices(edgeID);

        float weight = entityNodeIDs.parallelStream()
                .map(entityNodeID -> {
                    IntSet neighborNodeIDs = graph.getNeighbours(entityNodeID);
                    neighborNodeIDs.retainAll(entityNodeIDs);
                    return (float) neighborNodeIDs.size() / entityNodeIDs.size();
                })
                .reduce(0f, (a, b) -> a + b);

        weight /= entityNodeIDs.size();

        return weight;
    }

    private float computeSynonymHyperEdgeWeight(int edgeID) {
        if (auxProperties.isSetted(edgeID)) {
            return 1f / (float) auxProperties.getValue(edgeID);
        }
        return 1f;
    }

    private float computeContextHyperEdgeWeight(int edgeID) {
        FloatList synSims = (FloatArrayList) auxProperties.getValue(edgeID);
        return (float) synSims.stream().mapToDouble(sim -> sim).average().orElse(0d);
    }

    private void computeHyperEdgeWeights() {
        logger.info("Computing hyperedge weights");
        for (int edgeID : graph.getEdges()) {
            Edge edge = edgeIndex.getKey(edgeID);
            if (edge instanceof DocumentEdge) {
                edgeWeights.setValue(edgeID, DEFAULT_DOCUMENT_EDGE_WEIGHT);
            } else if (edge instanceof ContainedInEdge) {
                edgeWeights.setValue(edgeID, computeContainedInHyperEdgeWeight(edgeID));
            } else if (edge instanceof RelatedToEdge) {
                edgeWeights.setValue(edgeID, computeRelatedToHyperEdgeWeight(edgeID));
                /*logger.warn("Using random weight for related-to edges (TESTING ONLY)");
                edgeWeights.setValue(edgeID, Math.random());*/
            } else if (edge instanceof SynonymEdge) {
                edgeWeights.setValue(edgeID, computeSynonymHyperEdgeWeight(edgeID));
            } else if (edge instanceof ContextEdge) {
                edgeWeights.setValue(edgeID, computeContextHyperEdgeWeight(edgeID));
            }
        }
    }

    private void computeWeights() {
        computeNodeWeights();
        computeHyperEdgeWeights();
    }

    private void createReachabilityIndex() {
        logger.info("Computing connected components and creating reachability index");
        ConnectedComponentsAlgorithm connectedComponentsAlgorithm = new ConnectedComponentsAlgorithm();
        Collection<IntSet> connectedComponents = connectedComponentsAlgorithm.compute(graph);
        for (IntSet connectedComponent : connectedComponents) {
            for (int nodeID : connectedComponent.toIntArray()) {
                reachabilityIndex.put(nodeID, connectedComponent);
            }
        }
    }

    private void removeNodeAndUpdateHyperedges(int nodeID) {
        for (int edgeID : graph.getEdgesIncidentTo(nodeID)) {
            if (graph.isDirectedHyperEdge(edgeID)) {
                if (graph.getDirectedHyperEdgeTail(edgeID).contains(nodeID)) {
                    graph.removeFromDirectedHyperEdgeTail(edgeID, nodeID);
                    if (graph.getDirectedHyperEdgeTail(edgeID).size() == 0) {
                        graph.removeEdge(edgeID);
                    }
                } else {
                    graph.removeFromDirectedHyperEdgeHead(edgeID, nodeID);
                    if (graph.getDirectedHyperEdgeHead(edgeID).size() == 0) {
                        graph.removeEdge(edgeID);
                    }
                }
            } else {
                graph.removeFromHyperEdge(edgeID, nodeID);
                if (graph.getUndirectedHyperEdgeVertices(edgeID).size() == 0) {
                    graph.removeEdge(edgeID);
                }
            }
        }
        graph.removeVertex(nodeID);
    }

    private void prune() throws IOException {
        File pruneConfigFile = Paths.get(this.featuresPath, "prune.yml").toFile();
        PruneConfig pruneConfig = PruneConfig.load(pruneConfigFile);

        logger.info("Pruning hypergraph nodes and edges based on configuration file: {}", pruneConfigFile);

        int removedVertices = 0;
        for (int nodeID : graph.getVertices()) {
            float weight = nodeWeights.getValueAsFloat(nodeID);
            Node node = nodeIndex.getKey(nodeID);
            float threshold = pruneConfig.getNodeThreshold(node.getClass());
            if (weight < threshold) {
                removeNodeAndUpdateHyperedges(nodeID);
                removedVertices++;
            }
        }

        int removedEdges = 0;
        for (int edgeID : graph.getEdges()) {
            float weight = edgeWeights.getValueAsFloat(edgeID);
            Edge edge = edgeIndex.getKey(edgeID);
            float threshold = pruneConfig.getEdgeThreshold(edge.getClass());
            if (weight < threshold) {
                graph.removeEdge(edgeID);
                removedEdges++;
            }
        }

        logger.info("{} nodes pruned and {} hyperedges pruned", removedVertices, removedEdges);
    }

    @Override
    public void postProcessing() throws Exception {
        linkTextAndKnowledge();

        for (Feature feature : features) {
            switch (feature) {
                case SYNONYMS:
                    linkSynonyms();
                    break;
                case CONTEXT:
                    linkContextuallySimilarTerms();
                    break;
                case WEIGHT:
                    computeWeights();
                    break;
                case PRUNE:
                    prune();
                    break;
            }
        }

        // FIXME Requires too much memory to compute, but since it's only used for entityWeight, I disabled it.
        // TODO Consider deprecating or completely removing entityWeight from HGoE.
        //createReachabilityIndex();
    }

    @Override
    public void indexCorpus(Collection<Document> corpus) {
        corpus.parallelStream().forEach(document -> {
            try {
                index(document);
            } catch (IOException e) {
                logger.warn("Error indexing document {}, skpping", document.getDocID(), e);
            }
        });
    }

    @Override
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

        File nodeIndexFile = new File(directory, "node.idx");
        try {
            ObjectOutputStream output = new ObjectOutputStream(new FileOutputStream(nodeIndexFile));
            output.writeObject(nodeIndex);
            output.close();
        } catch (IOException e) {
            logger.error("Unable to dump node index to {}", nodeIndexFile, e);
        }

        File edgeIndexFile = new File(directory, "edge.idx");
        try {
            ObjectOutputStream output = new ObjectOutputStream(new FileOutputStream(edgeIndexFile));
            output.writeObject(edgeIndex);
            output.close();
        } catch (IOException e) {
            logger.error("Unable to dump edge index to {}", edgeIndexFile, e);
        }

        File reachabilityIndexFile = new File(directory, "reachability.idx");
        try {
            ObjectOutputStream output = new ObjectOutputStream(new FileOutputStream(reachabilityIndexFile));
            output.writeObject(reachabilityIndex);
            output.close();
        } catch (IOException e) {
            logger.error("Unable to dump reachability index to {}", reachabilityIndexFile, e);
        }

        File nodeWeightsFile = new File(directory, "node_weights.prp");
        try {
            ObjectOutputStream output = new ObjectOutputStream(new FileOutputStream(nodeWeightsFile));
            output.writeObject(nodeWeights);
            output.close();
        } catch (IOException e) {
            logger.error("Unable to dump node weights to {}", nodeWeightsFile, e);
        }

        File edgeWeightsFile = new File(directory, "edge_weights.prp");
        try {
            ObjectOutputStream output = new ObjectOutputStream(new FileOutputStream(edgeWeightsFile));
            output.writeObject(edgeWeights);
            output.close();
        } catch (IOException e) {
            logger.error("Unable to dump edge weights to {}", edgeWeightsFile, e);
        }

        File hypergraphFile = new File(directory, "hypergraph.graph");
        try {
            ObjectOutputStream output = new ObjectOutputStream(new FileOutputStream(hypergraphFile));
            output.writeObject(graph);
            output.close();
        } catch (IOException e) {
            logger.error("Unable to dump hypergraph to {}", hypergraphFile, e);
        }
    }

    public boolean load() {
        logger.info("Loading index from {}", directory.getAbsolutePath());

        File nodeIndexFile = new File(directory, "node.idx");
        try {
            ObjectInputStream input = new ObjectInputStream(new FileInputStream(nodeIndexFile));
            this.nodeIndex = (BidiMap) input.readObject();
            input.close();
        } catch (ClassNotFoundException | IOException e) {
            logger.warn("Cannot read node index from {}", nodeIndexFile);
            return false;
        }

        File edgeIndexFile = new File(directory, "edge.idx");
        try {
            ObjectInputStream input = new ObjectInputStream(new FileInputStream(edgeIndexFile));
            this.edgeIndex = (BidiMap) input.readObject();
            input.close();
        } catch (ClassNotFoundException | IOException e) {
            logger.warn("Cannot read edge index from {}", edgeIndexFile);
            return false;
        }

        File reachabilityIndexFile = new File(directory, "reachability.idx");
        try {
            ObjectInputStream input = new ObjectInputStream(new FileInputStream(reachabilityIndexFile));
            this.reachabilityIndex = (Map) input.readObject();
            input.close();
        } catch (ClassNotFoundException | IOException e) {
            logger.warn("Cannot read  reachability index from {}", reachabilityIndexFile);
            return false;
        }

        File nodeWeightsFile = new File(directory, "node_weights.prp");
        try {
            ObjectInputStream input = new ObjectInputStream(new FileInputStream(nodeWeightsFile));
            this.nodeWeights = (NumericalProperty) input.readObject();
            input.close();
        } catch (ClassNotFoundException | IOException e) {
            logger.warn("Cannot read node weights from {}", nodeWeightsFile);
            return false;
        }

        File edgeWeightsFile = new File(directory, "edge_weights.prp");
        try {
            ObjectInputStream input = new ObjectInputStream(new FileInputStream(edgeWeightsFile));
            this.edgeWeights = (NumericalProperty) input.readObject();
            input.close();
        } catch (ClassNotFoundException | IOException e) {
            logger.warn("Cannot read edge weights from {}", edgeWeightsFile);
            return false;
        }

        File hypergraphFile = new File(directory, "hypergraph.graph");
        try {
            ObjectInputStream input = new ObjectInputStream(new FileInputStream(hypergraphFile));
            this.graph = (InMemoryGrph) input.readObject();
            input.close();
        } catch (ClassNotFoundException | IOException e) {
            logger.warn("Cannot read hypergraph from {}", hypergraphFile);
            return false;
        }

        return true;
    }

    private IntSet getQueryTermNodeIDs(List<String> terms) {
        IntSet termNodes = new LucIntHashSet(10);

        for (String term : terms) {
            TermNode termNode = new TermNode(term);
            if (nodeIndex.containsKey(termNode)) {
                termNodes.add(nodeIndex.get(termNode).intValue());
            }
        }

        return termNodes;
    }

    public boolean containsNode(Node node) {
        return nodeIndex.containsKey(node);
    }

    private IntSet getSeedNodeIDs(IntSet queryTermNodeIDs) {
        IntSet seedNodes = new LucIntHashSet(10);

        for (Integer queryTermNode : queryTermNodeIDs) {
            IntSet localSeedNodes = new LucIntHashSet(10);

            IntSet edgeIDs;
            if (graph.containsVertex(queryTermNode)) {
                edgeIDs = graph.getOutEdges(queryTermNode);
            } else {
                edgeIDs = new IntOpenHashSet();
            }

            for (int edgeID : edgeIDs) {
                Edge edge = edgeIndex.getKey(edgeID);

                if (!(edge instanceof ContainedInEdge)) continue;

                for (int nodeID : graph.getDirectedHyperEdgeHead(edgeID)) {
                    Node node = nodeIndex.getKey(nodeID);
                    if (node instanceof EntityNode) {
                        localSeedNodes.add(nodeID);
                    }
                }
            }

            if (localSeedNodes.isEmpty() && graph.containsVertex(queryTermNode)) {
                localSeedNodes.add(queryTermNode.intValue());
            }

            seedNodes.addAll(localSeedNodes);
        }

        return seedNodes;
    }

    // XXX HERE
    private double coverage(int entityNodeID, IntSet seedNodeIDs) {
        if (seedNodeIDs.isEmpty()) return 0d;

        IntSet reachableSeedNodeIDs = new IntOpenHashSet(reachabilityIndex.get(entityNodeID));
        reachableSeedNodeIDs.retainAll(seedNodeIDs);

        return (double) reachableSeedNodeIDs.size() / seedNodeIDs.size();
    }

    // TODO Can be improved with an edge index per edge type: Map<Class<? extends Edge>, Set<Integer>>
    private IntSet getUndirectedNeighborsPerEdgeType(int sourceNodeID, Class edgeType) {
        IntSet result = new LucIntHashSet(10);
        result.addAll(graph.getEdgesIncidentTo(sourceNodeID).stream()
                .filter(edgeID -> {
                    Edge edge = edgeIndex.getKey(edgeID);
                    return edgeType.isInstance(edge);
                })
                .flatMap(edgeID -> {
                    IntSet nodeIDs = new LucIntHashSet(10);
                    if (graph.isDirectedHyperEdge(edgeID)) {
                        nodeIDs.addAll(graph.getVerticesIncidentToEdge(edgeID));
                    } else {
                        nodeIDs.addAll(graph.getUndirectedHyperEdgeVertices(edgeID));
                    }
                    return nodeIDs.stream().filter(nodeID -> !nodeID.equals(sourceNodeID));
                })
                .collect(Collectors.toSet()));
        return result;
    }

    private double confidenceWeight(int seedNodeID, IntSet queryTermNodeIDs) {
        Node seedNode = nodeIndex.getKey(seedNodeID);

        if (seedNode == null) return 0;

        if (seedNode instanceof TermNode) return 1;

        IntSet neighborIDs = getUndirectedNeighborsPerEdgeType(seedNodeID, ContainedInEdge.class);

        IntSet linkedQueryTermNodes = new LucIntHashSet(10);
        linkedQueryTermNodes.addAll(neighborIDs);
        linkedQueryTermNodes.retainAll(queryTermNodeIDs);

        //if (neighborIDs.isEmpty()) return 0;

        return (double) linkedQueryTermNodes.size() / neighborIDs.size();
    }

    public Map<Integer, Double> seedNodeConfidenceWeights(IntSet seedNodeIDs, IntSet queryTermNodeIDs) {
        Map<Integer, Double> weights = new HashMap<>();

        for (int seedNode : seedNodeIDs) {
            weights.put(seedNode, confidenceWeight(seedNode, queryTermNodeIDs));
        }

        return weights;
    }

    // FIXME getShortestPath() does not seem to work with hyperedges.
    private double perSeedScoreDijkstra(int entityNodeID, int seedNodeID, double seedWeight) {
        double perSeedScore = 0d;
        grph.path.Path shortestPath = graph.getShortestPath(entityNodeID, seedNodeID);
        if (shortestPath != null) perSeedScore = seedWeight * 1d / (1 + shortestPath.getLength());
        return perSeedScore;
    }

    // FIXME AllPaths does not work with hyperedges.
    private double perSeedScoreAllPaths(int entityNodeID, int seedNodeID, double seedWeight) {
        double perSeedScore = 0d;

        List<grph.path.Path> paths = AllPaths.compute(entityNodeID, graph, SEARCH_MAX_DISTANCE, MAX_PATHS_PER_PAIR, false)
                .stream()
                .flatMap(Collection::stream)
                .filter(path -> path.containsVertex(seedNodeID))
                .collect(Collectors.toList());

        for (grph.path.Path path : paths) {
            perSeedScore += seedWeight * 1d / (1 + path.getLength());
        }
        perSeedScore /= 1 + paths.size();

        return perSeedScore;
    }

    // TODO Should follow Bellaachia2013 for random walks on hypergraphs (Equation 14)
    private grph.path.Path randomWalk(int startNodeID, int length, boolean useWeightBias) {
        grph.path.Path path = new ArrayListPath();
        path.extend(startNodeID);
        randomStep(startNodeID, length, path, useWeightBias);
        return path;
    }

    private void randomStep(int nodeID, int remainingSteps, grph.path.Path path, boolean useWeightBias) {
        if (remainingSteps == 0) return;

        IntSet edgeIDs = graph.getOutEdges(nodeID);

        if (edgeIDs.isEmpty()) return;
        int randomEdgeID;
        if (useWeightBias) {
            Float[] edgeWeights = edgeIDs.stream().map(this.edgeWeights::getValueAsFloat).toArray(Float[]::new);
            randomEdgeID = sampleNonUniformlyAtRandom(edgeIDs.toIntArray(), ArrayUtils.toPrimitive(edgeWeights));
        } else {
            randomEdgeID = sampleUniformlyAtRandom(edgeIDs.toIntArray());
        }

        IntSet nodeIDs = new LucIntHashSet(10);
        if (graph.isDirectedHyperEdge(randomEdgeID)) {
            nodeIDs.addAll(graph.getDirectedHyperEdgeHead(randomEdgeID));
        } else {
            nodeIDs.addAll(graph.getUndirectedHyperEdgeVertices(randomEdgeID));
            nodeIDs.remove(nodeID);
        }

        if (nodeIDs.isEmpty()) return;
        int randomNodeID;
        if (useWeightBias) {
            Float[] nodeWeights = nodeIDs.stream().map(this.nodeWeights::getValueAsFloat).toArray(Float[]::new);
            randomNodeID = sampleNonUniformlyAtRandom(nodeIDs.toIntArray(), ArrayUtils.toPrimitive(nodeWeights));
        } else {
            randomNodeID = sampleUniformlyAtRandom(nodeIDs.toIntArray());
        }

        path.extend(randomEdgeID, randomNodeID);
        randomStep(randomNodeID, remainingSteps - 1, path, useWeightBias);
    }

    public ResultSet randomWalkSearch(IntSet seedNodeIDs, Map<Integer, Double> seedNodeWeights,
                                      int walkLength, int walkRepeats, boolean biased) {
        logger.info("walkLength = {}, walkRepeats = {}", walkLength, walkRepeats);

        Int2FloatOpenHashMap weightedNodeVisitProbability = new Int2FloatOpenHashMap();
        Int2DoubleOpenHashMap nodeCoverage = new Int2DoubleOpenHashMap();

        trace.add("Random walk search (l = %d, r = %d)", walkLength, walkRepeats);
        trace.goDown();

        for (int seedNodeID : seedNodeIDs) {
            Int2IntOpenHashMap nodeVisits = new Int2IntOpenHashMap();
            trace.add("From seed node: %s", nodeIndex.getKey(seedNodeID));
            /*trace.goDown();
            trace.add("Random walk with repeat (walkLength = %d, walkRepeats = %d)", walkLength, walkRepeats);
            trace.goDown();*/

            for (int i = 0; i < walkRepeats; i++) {
                grph.path.Path randomPath = randomWalk(seedNodeID, walkLength, biased);

                /*String messageRandomPath = Arrays.stream(randomPath.toVertexArray())
                        .mapToObj(nodeID -> nodeIndex.getKey(nodeID).toString())
                        .collect(Collectors.joining        //IntSet edgeIDs = graph.getEdgesIncidentTo(nodeID);
(" -> "));
                trace.add(messageRandomPath.replace("%", "%%"));
                trace.goDown();*/

                for (int nodeID : randomPath.toVertexArray()) {
                    nodeVisits.addTo(nodeID, 1);
                    //trace.add("Node %s visited %d times", nodeIndex.getKey(nodeID), nodeVisits.get(nodeID));
                }

                //trace.goUp();
            }

            //trace.goUp();

            int maxVisits = Arrays.stream(nodeVisits.values().toIntArray()).max().orElse(0);
            trace.goDown();
            trace.add("max(visits) = %d", maxVisits);

            /*trace.add("Accumulating visit probability, weighted by seed node confidence");
            trace.goDown();*/
            for (int nodeID : nodeVisits.keySet()) {
                nodeCoverage.addTo(nodeID, 1);
                synchronized (this) {
                    weightedNodeVisitProbability.compute(
                            nodeID, (k, v) -> (v == null ? 0 : v) + (float) nodeVisits.get(nodeID) / maxVisits * seedNodeWeights.get(seedNodeID).floatValue());
                }
                /*trace.add("score(%s) += visits(%s) * w(%s)",
                        nodeIndex.getKey(nodeID),
                        nodeIndex.getKey(nodeID),
                        nodeIndex.getKey(seedNodeID));
                trace.goDown();
                trace.add("P(visit(%s)) = %f", nodeIndex.getKey(nodeID).toString(), (float) nodeVisits.get(nodeID) / maxVisits);
                trace.add("w(%s) = %f", nodeIndex.getKey(seedNodeID), seedNodeWeights.get(seedNodeID));
                trace.add("score(%s) = %f", nodeIndex.getKey(nodeID), weightedNodeVisitProbability.get(nodeID));
                trace.goUp();*/
            }

            trace.add("%d visited nodes", nodeVisits.size());
            trace.goUp();

            /*trace.goUp();
            trace.goUp();*/
        }

        trace.goUp();

        ResultSet resultSet = new ResultSet();
        resultSet.setTrace(trace);

        trace.add("Weighted nodes");
        trace.goDown();

        double maxCoverage = Arrays.stream(nodeCoverage.values().toDoubleArray()).max().orElse(0d);
        trace.add("max(coverage) = %f", maxCoverage);

        for (int nodeID : weightedNodeVisitProbability.keySet()) {
            nodeCoverage.compute(nodeID, (k, v) -> v / maxCoverage);

            Node node = nodeIndex.getKey(nodeID);
            trace.add(node.toString().replace("%", "%%"));
            trace.goDown();
            trace.add("score = %f", weightedNodeVisitProbability.get(nodeID));
            trace.add("coverage = %f", nodeCoverage.get(nodeID));
            trace.goUp();

            if (node instanceof EntityNode) {
                EntityNode entityNode = (EntityNode) node;
                logger.debug("Ranking {} using RANDOM_WALK_SCORE", entityNode);
                double score = nodeCoverage.get(nodeID) * weightedNodeVisitProbability.get(nodeID);
                if (score > PROBABILITY_THRESHOLD && entityNode.hasDocID()) {
                    resultSet.addReplaceResult(new Result(score, entityNode, entityNode.getDocID()));
                }
                /*if (score > PROBABILITY_THRESHOLD) {
                    if (entityNode.hasDocID()) {
                        resultSet.addReplaceResult(new Result(score, entityNode, entityNode.getDocID()));
                    } else {
                        resultSet.addReplaceResult(new Result(score, entityNode, entityNode.getName()));
                    }
                }*/
            }
        }

        trace.goUp();

        trace.add("Collecting results (class=EntityNode; hasDocID()=true)");
        trace.goDown();

        for (Result result : resultSet) {
            trace.add(result.getNode().toString());
            trace.goDown();
            trace.add("score = %f", result.getScore());
            trace.add("docID = %s", result.getDocID());
            trace.add("nodeID = %d", nodeIndex.get(result.getNode()));
            trace.goUp();
        }

        return resultSet;
    }

    public double entityWeight(int entityNodeID, IntSet seedNodeIDs, Map<Integer, Double> seedNodeWeights) {
        return entityWeight(entityNodeID, seedNodeIDs, seedNodeWeights, true, PerSeedScoreMethod.ALL_PATHS);
    }

    // FIXME ALL_PATHS and DIJKSTRA do not work for hypergraphs
    public double entityWeight(int entityNodeID, IntSet seedNodeIDs, Map<Integer, Double> seedNodeWeights,
                               boolean withCoverage, PerSeedScoreMethod method) {
        double score = 0d;

        // Get all paths between the entity and a seed node (within a maximum distance; null by default).
        for (Map.Entry<Integer, Double> entry : seedNodeWeights.entrySet()) {
            int seedNodeID = entry.getKey();
            double seedWeight = entry.getValue();
            switch (method) {
                case ALL_PATHS:
                    score += perSeedScoreAllPaths(entityNodeID, seedNodeID, seedWeight);
                case DIJKSTA:
                    score += perSeedScoreDijkstra(entityNodeID, seedNodeID, seedWeight);
            }
        }

        score = seedNodeWeights.isEmpty() ? 0 : score / seedNodeWeights.size();
        if (withCoverage) score *= coverage(entityNodeID, seedNodeIDs);

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

    private double jaccardSimilarity(IntSet a, IntSet b) {
        IntSet intersect = new IntOpenHashSet(a);
        intersect.retainAll(b);

        IntSet union = new IntOpenHashSet(a);
        union.addAll(b);

        return (double) intersect.size() / union.size();
    }

    // Neighborhood does not account for direction.
    public double jaccardScore(int entityNodeID, Map<Integer, Double> seedNodeWeights) {
        Map<Integer, Pair<IntSet, Double>> seedNeighborsWeights = new HashMap<>();
        for (Map.Entry<Integer, Double> entry : seedNodeWeights.entrySet()) {
            seedNeighborsWeights.put(entry.getKey(), Pair.of(graph.getNeighbours(entry.getKey()), entry.getValue()));
        }

        IntSet entityNeighbors = graph.getNeighbours(entityNodeID);

        return seedNeighborsWeights.entrySet().stream().map(seed -> {
            IntSet seedNeighbors = seed.getValue().getLeft();
            return seed.getValue().getRight() * jaccardSimilarity(seedNeighbors, entityNeighbors);
        }).mapToDouble(f -> f).sum();
    }

    public ResultSet entityIteratorSearch(IntSet seedNodeIDs, Map<Integer, Double> seedNodeWeights,
                                          RankingFunction function) {
        ResultSet resultSet = new ResultSet();
        resultSet.setTrace(trace);

        graph.getVertices().parallelStream().forEach(nodeID -> {
            Node node = nodeIndex.getKey(nodeID);
            if (node instanceof EntityNode) {
                EntityNode entityNode = (EntityNode) node;
                logger.debug("Ranking {} using {}", entityNode, function);

                double score;
                switch (function) {
                    case ENTITY_WEIGHT:
                        score = entityWeight(nodeID, seedNodeIDs, seedNodeWeights);
                        break;
                    case JACCARD_SCORE:
                        score = jaccardScore(nodeID, seedNodeWeights);
                        break;
                    default:
                        logger.warn("Ranking function {} is unsupported for entity iterator search", function);
                        score = 0d;
                }

                if (score > 0 && entityNode.hasDocID()) {
                    synchronized (this) {
                        resultSet.addReplaceResult(new Result(score, entityNode, entityNode.getDocID()));
                    }
                }
            }
        });

        return resultSet;
    }

    @Override
    public ResultSet search(String query, int offset, int limit) throws IOException {
        Map<String, String> params = new HashMap<>();
        params.put("l", String.valueOf(DEFAULT_WALK_LENGTH));
        params.put("r", String.valueOf(DEFAULT_WALK_REPEATS));
        return search(query, offset, limit, RankingFunction.RANDOM_WALK_SCORE, params);
    }

    public ResultSet search(String query, int offset, int limit, RankingFunction function, Map<String, String> params) throws IOException {
        long start = System.currentTimeMillis();
        trace.reset();

        List<String> tokens = analyze(query);
        IntSet queryTermNodeIDs = getQueryTermNodeIDs(tokens);
        trace.add("Mapping query terms [ %s ] to query term nodes", StringUtils.join(tokens, ", "));
        trace.goDown();
        for (int queryTermNodeID : queryTermNodeIDs) {
            trace.add(nodeIndex.getKey(queryTermNodeID).toString());
        }
        trace.goUp();

        IntSet seedNodeIDs = getSeedNodeIDs(queryTermNodeIDs);
        //System.out.println("Seed Nodes: " + seedNodeIDs.stream().map(nodeID -> nodeID + "=" + nodeIndex.getKey(nodeID).toString()).collect(Collectors.toList()));
        trace.add("Mapping query term nodes to seed nodes");
        trace.goDown();
        for (int seedNodeID : seedNodeIDs) {
            trace.add(nodeIndex.getKey(seedNodeID).toString().replace("%", "%%"));
        }
        trace.goUp();

        Map<Integer, Double> seedNodeWeights = seedNodeConfidenceWeights(seedNodeIDs, queryTermNodeIDs);
        //System.out.println("Seed Node Confidence Weights: " + seedNodeWeights);
        logger.info("{} seed nodes weights calculated for [ {} ]", seedNodeWeights.size(), query);
        trace.add("Calculating confidence weight for seed nodes");
        trace.goDown();
        for (Map.Entry<Integer, Double> entry : seedNodeWeights.entrySet()) {
            trace.add("w(%s) = %f", nodeIndex.getKey(entry.getKey()), entry.getValue());
        }
        trace.goUp();

        ResultSet resultSet;
        switch (function) {
            case RANDOM_WALK_SCORE:
            case BIASED_RANDOM_WALK_SCORE:
                resultSet = randomWalkSearch(
                        seedNodeIDs, seedNodeWeights,
                        Integer.valueOf(params.getOrDefault("l", String.valueOf(DEFAULT_WALK_LENGTH))),
                        Integer.valueOf(params.getOrDefault("r", String.valueOf(DEFAULT_WALK_REPEATS))),
                        function == RankingFunction.BIASED_RANDOM_WALK_SCORE);
                break;
            case ENTITY_WEIGHT:
            case JACCARD_SCORE:
                resultSet = entityIteratorSearch(seedNodeIDs, seedNodeWeights, function);
                break;
            default:
                logger.warn("Ranking function {} is unsupported", function);
                resultSet = ResultSet.empty();
        }

        long end = System.currentTimeMillis();

        logger.info("{} entities ranked for [ {} ] in {}ms", resultSet.getNumDocs(), query, end - start);
        return resultSet;
    }

    public Trace getSummary() {
        Trace summary = new Trace("SUMMARY");

        /***
         * Nodes
         */

        summary.add("%10d nodes", graph.getNumberOfVertices());

        summary.goDown();

        Map<String, Integer> nodeCountPerType = new HashMap<>();
        for (int nodeID : graph.getVertices()) {
            nodeCountPerType.compute(
                    nodeIndex.getKey(nodeID).getClass().getSimpleName(),
                    (k, v) -> {
                        if (v == null) v = 1;
                        else v += 1;
                        return v;
                    });
        }

        for (Map.Entry<String, Integer> entry : nodeCountPerType.entrySet()) {
            summary.add("%10d %s", entry.getValue(), entry.getKey());
        }

        summary.goUp();

        /**
         * Hyperedges
         */

        summary.add("%10d hyperedges", graph.getNumberOfUndirectedHyperEdges() + graph.getNumberOfDirectedHyperEdges());
        summary.goDown();

        summary.add("%10d directed hyperedges", graph.getNumberOfDirectedHyperEdges());
        summary.goDown();

        Map<String, Integer> directedEdgeCountPerType = new HashMap<>();
        for (int edgeID : graph.getEdges()) {
            if (!graph.isDirectedHyperEdge(edgeID)) continue;

            directedEdgeCountPerType.compute(
                    edgeIndex.getKey(edgeID).getClass().getSimpleName(),
                    (k, v) -> {
                        if (v == null) v = 1;
                        else v += 1;
                        return v;
                    });
        }

        for (Map.Entry<String, Integer> entry : directedEdgeCountPerType.entrySet()) {
            summary.add("%10d %s", entry.getValue(), entry.getKey());
        }

        summary.goUp();

        summary.add("%10d undirected hyperedges", graph.getNumberOfUndirectedHyperEdges());
        summary.goDown();

        Map<String, Integer> undirectedEdgeCountPerType = new HashMap<>();
        for (int edgeID : graph.getEdges()) {
            if (graph.isDirectedHyperEdge(edgeID)) continue;

            undirectedEdgeCountPerType.compute(
                    edgeIndex.getKey(edgeID).getClass().getSimpleName(),
                    (k, v) -> {
                        if (v == null) v = 1;
                        else v += 1;
                        return v;
                    });
        }

        for (Map.Entry<String, Integer> entry : undirectedEdgeCountPerType.entrySet()) {
            summary.add("%10d %s", entry.getValue(), entry.getKey());
        }

        return summary;
    }

    /**
     * How many synonyms (i.e., terms in the tail of a SynonymEdge) link terms in two or more documents?
     * How many distinct documents on average do synonym terms link?
     *
     * @return Synonym information trace.
     */
    public Trace getSummaryByUndirectedEdgeType(Class nodeType, Class edgeType) {
        assert nodeType == Node.class || nodeType == TermNode.class;
        assert edgeType == SynonymEdge.class || edgeType == ContextEdge.class;

        String edgeTypeStr = edgeType.getSimpleName().replace("Edge", "").toLowerCase();

        Trace summary = new Trace(String.format("%s SUMMARY", edgeTypeStr.toUpperCase()));

        if ((edgeType == SynonymEdge.class && !features.contains(Feature.SYNONYMS))
            || (edgeType == ContextEdge.class && !features.contains(Feature.CONTEXT))) {
            summary.add("Feature disabled in this index");
            return summary;
        }

        Map<Integer, Set<Integer>> baseToDocs = new HashMap<>();

        // Iterate over all term nodes
        for (int baseTermNodeID : graph.getVertices()) {
            Node baseTermNode = nodeIndex.getKey(baseTermNodeID);
            if (baseTermNode instanceof TermNode) {
                // Iterate over all synonym hyperedges leaving term node (i.e., term node is a synonym)
                for (int baseEdgeID : graph.getOutEdges(baseTermNodeID)) {
                    Edge baseEdge = edgeIndex.getKey(baseEdgeID);
                    if (edgeType.isInstance(baseEdge)) {
                        int neighborNodeID = graph.getUndirectedHyperEdgeVertices(baseEdgeID).getGreatest();
                        Node neighborNode = nodeIndex.getKey(neighborNodeID);

                        if (nodeType.isInstance(neighborNode)) {
                            // Obtain term node document neighbors
                            for (int docNodeID : graph.getInNeighbors(neighborNodeID)) {
                                Node docNode = nodeIndex.getKey(docNodeID);
                                if (docNode instanceof DocumentNode) {
                                    baseToDocs.computeIfAbsent(baseTermNodeID, k ->
                                            new HashSet<>(Collections.singletonList(docNodeID)));
                                    baseToDocs.computeIfPresent(baseTermNodeID, (k, v) -> {
                                        v.add(docNodeID);
                                        return v;
                                    });
                                }
                            }
                        }
                    }
                }
            }
        }

        long pathsBetweenDocs = baseToDocs.entrySet().stream()
                .filter(entry -> entry.getValue().size() > 1)
                .count();

        summary.add("%10d paths established between documents", pathsBetweenDocs);

        IntSummaryStatistics statsLinkedDocsPerEdgeType = baseToDocs.values().stream()
                .mapToInt(Set::size)
                .summaryStatistics();

        summary.add("%10.2f documents linked on average per %s", statsLinkedDocsPerEdgeType.getAverage(), edgeTypeStr);
        summary.goDown();
        summary.add("%10d minimum documents linked per %s", statsLinkedDocsPerEdgeType.getMin(), edgeTypeStr);
        summary.add("%10d maximum documents linked per %s", statsLinkedDocsPerEdgeType.getMax(), edgeTypeStr);

        return summary;
    }

    public Trace getNodeList() {
        Trace summary = new Trace("Nodes");

        Class[] nodeClasses = {DocumentNode.class, TermNode.class, EntityNode.class};

        for (Class nodeClass : nodeClasses) {
            summary.add(nodeClass.getSimpleName());
            summary.goDown();

            for (int nodeID : graph.getVertices()) {
                Node node = nodeIndex.getKey(nodeID);
                if (nodeClass.isInstance(node)) {
                    double nodeWeight = nodeWeights.getValueAsFloat(nodeID);
                    summary.add("%10d %.2f %s", nodeID, nodeWeight, node.getName());
                }
            }

            summary.goUp();
        }

        return summary;
    }

    public Trace getHyperedgeList() {
        Trace summary = new Trace("Hyperedges");

        Class[] hyperedgeClasses = {DocumentEdge.class, RelatedToEdge.class, ContainedInEdge.class};

        for (Class edgeClass : hyperedgeClasses) {
            summary.add(edgeClass.getSimpleName());
            summary.goDown();

            for (int edgeID : graph.getEdges()) {
                Edge edge = edgeIndex.getKey(edgeID);

                if (edgeClass.isInstance(edge)) {
                    float edgeWeight = edgeWeights.getValueAsFloat(edgeID);

                    if (graph.isDirectedHyperEdge(edgeID)) {
                        Set<String> tail = graph.getDirectedHyperEdgeTail(edgeID).stream()
                                .map(nodeID -> nodeIndex.getKey(nodeID).getName())
                                .collect(Collectors.toSet());

                        Set<String> head = graph.getDirectedHyperEdgeHead(edgeID).stream()
                                .map(nodeID -> nodeIndex.getKey(nodeID).getName())
                                .collect(Collectors.toSet());

                        summary.add("%10d %.2f %s -> %s", edgeID, edgeWeight, tail, head);
                    } else {
                        Set<String> nodes = graph.getUndirectedHyperEdgeVertices(edgeID).stream()
                                .map(nodeID -> nodeIndex.getKey(nodeID).getName())
                                .collect(Collectors.toSet());
                        summary.add("%10d %.2f %s", edgeID, edgeWeight, nodes);
                    }
                }
            }

            summary.goUp();
        }

        return summary;
    }

    @Override
    public void inspect(String feature) {
        boolean valid = true;
        Trace trace = null;
        if (feature.equals("summary")) {
            trace = getSummary();
        } else if (feature.equals("synonym-summary")) {
            trace = getSummaryByUndirectedEdgeType(TermNode.class, SynonymEdge.class);
        } else if (feature.equals("context-summary")) {
            trace = getSummaryByUndirectedEdgeType(TermNode.class, ContextEdge.class);
        } else if (feature.equals("list-nodes")) {
            trace = getNodeList();
        } else if (feature.equals("list-hyperedges")) {
            trace = getHyperedgeList();
        } else {
            valid = false;
        }

        if (valid) {
            System.out.println("\n================== Hypergraph-of-Entity ==================\n");
            System.out.println(trace.toASCII());
        } else {
            logger.error("Invalid feature {}", feature);
        }
    }

    private enum PerSeedScoreMethod {
        DIJKSTA,
        ALL_PATHS
    }

    public enum RankingFunction {
        ENTITY_WEIGHT,
        JACCARD_SCORE,
        RANDOM_WALK_SCORE,
        BIASED_RANDOM_WALK_SCORE
    }

    public enum Feature {
        SYNONYMS,
        CONTEXT,
        WEIGHT,
        PRUNE
    }
}
