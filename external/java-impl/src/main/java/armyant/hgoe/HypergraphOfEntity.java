package armyant.hgoe;

import java.io.BufferedWriter;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.ObjectInputStream;
import java.io.ObjectOutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;
import java.util.Date;
import java.util.HashMap;
import java.util.HashSet;
import java.util.IntSummaryStatistics;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import java.util.stream.Collectors;
import java.util.stream.IntStream;
import java.util.zip.GZIPInputStream;

import javax.xml.parsers.ParserConfigurationException;

import org.ahocorasick.trie.Emit;
import org.ahocorasick.trie.Trie;
import org.apache.commons.collections4.BidiMap;
import org.apache.commons.collections4.bidimap.DualHashBidiMap;
import org.apache.commons.collections4.trie.PatriciaTrie;
import org.apache.commons.csv.CSVFormat;
import org.apache.commons.csv.CSVPrinter;
import org.apache.commons.io.FileUtils;
import org.apache.commons.lang3.ArrayUtils;
import org.apache.commons.lang3.StringUtils;
import org.apache.commons.lang3.tuple.Pair;
import org.apache.commons.math3.analysis.function.Sigmoid;
import org.apache.commons.math3.stat.StatUtils;
import org.apache.commons.math3.stat.descriptive.DescriptiveStatistics;
import org.apache.commons.math3.stat.descriptive.rank.Percentile;
import org.apache.tinkerpop.gremlin.structure.Direction;
import org.apache.tinkerpop.gremlin.structure.Vertex;
import org.apache.tinkerpop.gremlin.structure.io.IoCore;
import org.apache.tinkerpop.gremlin.tinkergraph.structure.TinkerGraph;
import org.apache.tinkerpop.gremlin.util.iterator.IteratorUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.xml.sax.SAXException;

import armyant.Engine;
import armyant.hgoe.edges.ContainedInEdge;
import armyant.hgoe.edges.ContextEdge;
import armyant.hgoe.edges.DocumentEdge;
import armyant.hgoe.edges.Edge;
import armyant.hgoe.edges.RelatedToEdge;
import armyant.hgoe.edges.SentenceEdge;
import armyant.hgoe.edges.SynonymEdge;
import armyant.hgoe.edges.TFBinEdge;
import armyant.hgoe.exceptions.HypergraphException;
import armyant.hgoe.nodes.EntityNode;
import armyant.hgoe.nodes.Node;
import armyant.hgoe.nodes.TermNode;
import armyant.structures.Document;
import armyant.structures.Entity;
import armyant.structures.Result;
import armyant.structures.ResultSet;
import armyant.structures.Trace;
import armyant.structures.Triple;
import armyant.structures.yaml.PruneConfig;
import armyant.structures.yaml.TFBinsConfig;
import armyant.util.ClusteringCoefficientAccumulator;
import armyant.util.DecompressibleInputStream;
import edu.mit.jwi.IRAMDictionary;
import edu.mit.jwi.RAMDictionary;
import edu.mit.jwi.data.ILoadPolicy;
import edu.mit.jwi.item.IIndexWord;
import edu.mit.jwi.item.ISynset;
import edu.mit.jwi.item.IWord;
import edu.mit.jwi.item.IWordID;
import edu.mit.jwi.item.POS;
import grph.algo.AllPaths;
import grph.algo.ConnectedComponentsAlgorithm;
import grph.in_memory.InMemoryGrph;
import grph.io.ParseException;
import grph.path.ArrayListPath;
import grph.properties.NumericalProperty;
import it.unimi.dsi.fastutil.floats.FloatArrayList;
import it.unimi.dsi.fastutil.floats.FloatList;
import it.unimi.dsi.fastutil.ints.Int2DoubleOpenHashMap;
import it.unimi.dsi.fastutil.ints.Int2FloatOpenHashMap;
import it.unimi.dsi.fastutil.ints.Int2IntOpenHashMap;
import it.unimi.dsi.fastutil.ints.IntArrays;
import it.unimi.dsi.fastutil.ints.IntOpenHashSet;
import it.unimi.dsi.fastutil.ints.IntSet;
import toools.collections.primitive.IntCursor;
import toools.collections.primitive.LucIntHashSet;
import toools.collections.primitive.LucIntSet;
import toools.exceptions.NotYetImplementedException;

/**
 * Created by jldevezas on 2017-10-23.
 */
// TODO instaceof might be replaced by a Grph Property of some sort (is it faster?)
public class HypergraphOfEntity extends Engine {
    private static final Logger logger = LoggerFactory.getLogger(HypergraphOfEntity.class);
    private static final Sigmoid sigmoid = new Sigmoid();
    private static final SimpleDateFormat isoDateFormat = new SimpleDateFormat("yyyyMMdd'T'HHmmss");

    private static final int SEARCH_MAX_DISTANCE = 2;
    private static final int MAX_PATHS_PER_PAIR = 1000;

    private static final float DEFAULT_DOCUMENT_EDGE_WEIGHT = 0.5f;

    private static final int DEFAULT_WALK_LENGTH = 2;
    private static final int DEFAULT_WALK_REPEATS = 1000;
    private static final int DEFAULT_FATIQUE = 0;

    private static final float DEFAULT_DAMPING_FACTOR = 0.85f;
    private static final int DEFAULT_MAX_ITERATIONS = 10000;

    private static final int DEFAULT_TF_BINS = 2;

    private static final float PROBABILITY_THRESHOLD = 0.005f;

    private static final String CONTEXT_FEATURES_FILENAME = "word2vec_simnet.graphml.gz";

    private List<Feature> features;
    private String featuresPath;
    private EntityIndexingStrategy entityIndexingStrategy;
    private int tfBins;
    private File directory;
    private InMemoryGrph graph;
    private NumericalProperty nodeWeights;
    private NumericalProperty edgeWeights;
    private Map<Integer, Integer> nodeFatigueStatus;
    private Map<Integer, Integer> edgeFatigueStatus;
    private Map<Integer, Integer> synEdgeAux;
    private Map<Integer, FloatList> contextEdgeAux;
    private BidiMap<Node, Integer> nodeIndex;
    private BidiMap<Edge, Integer> edgeIndex;
    private Map<Integer, IntSet> reachabilityIndex;
    private PatriciaTrie<String> entityNameTrie;
    private Trace trace;

    private long counter;
    private long totalTime;
    private float avgTimePerDocument;

    private int numDocs;

    public HypergraphOfEntity(String path) throws HypergraphException {
        this(path, new ArrayList<>());
    }

    public HypergraphOfEntity(String path, List<Feature> features) throws HypergraphException {
        this(path, features, null, false);
    }

    public HypergraphOfEntity(String path, List<Feature> features, String featuresPath) throws HypergraphException {
        this(path, features, featuresPath, false);
    }

    public HypergraphOfEntity(String path, List<Feature> features, String featuresPath, boolean overwrite)
            throws HypergraphException {
        super();

        this.features = features;
        this.featuresPath = featuresPath;

        if (this.features.contains(Feature.RELATED_TO_BY_DOC)) {
            this.entityIndexingStrategy = EntityIndexingStrategy.DOCUMENT_COOCCURRENCE;
        } else if (this.features.contains(Feature.RELATED_TO_BY_SUBJ)) {
            this.entityIndexingStrategy = EntityIndexingStrategy.GROUP_BY_SUBJECT;
        } else {
            // Default here
            this.entityIndexingStrategy = EntityIndexingStrategy.GROUP_BY_SUBJECT;
        }

        if (this.features.contains(Feature.TF_BINS)) {
            File config = Paths.get(featuresPath, "tf_bins.yml").toFile();
            try {
                tfBins = TFBinsConfig.load(config).getBins();
                logger.info("Using {} TF-bins per document", tfBins);
            } catch (IOException e) {
                tfBins = DEFAULT_TF_BINS;
                logger.warn("Using default of {} TF-bins per document", tfBins);
            }
        }

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
        this.nodeWeights = new NumericalProperty("weight", 32, Float.floatToIntBits(0.5f));
        this.edgeWeights = new NumericalProperty("weight", 32, Float.floatToIntBits(0.5f));
        this.nodeFatigueStatus = new HashMap<>();
        this.edgeFatigueStatus = new HashMap<>();
        this.synEdgeAux = new HashMap<>();
        this.contextEdgeAux = new HashMap<>();
        this.nodeIndex = new DualHashBidiMap<>();
        this.edgeIndex = new DualHashBidiMap<>();
        this.reachabilityIndex = new HashMap<>();
        this.trace = new Trace();

        String featuresStr = features.isEmpty() ? "no features"
                : String.format("features: %s",
                        String.join(", ", features.stream().map(Feature::toString).toArray(String[]::new)));
        logger.info("Opening hypergraph-of-entity at {}, with {}", path, featuresStr);

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
        DocumentEdge documentEdge = new DocumentEdge(document.getDocID(), document.getTitle());
        int documentEdgeID = getOrCreateUndirectedEdge(documentEdge);

        // Deprecated, because the probability of visiting a document node is minimal.
        /*
         * DocumentNode documentNode = new DocumentNode(document.getDocID(), document.getTitle()); int
         * sourceDocumentNodeID = getOrCreateNode(documentNode); synchronized (this) {
         * graph.addToUndirectedHyperEdge(edgeID, sourceDocumentNodeID); }
         */

        Set<Integer> targetEntityNodeIDs = indexEntities(document);
        addNodesToUndirectedHyperEdge(documentEdgeID, targetEntityNodeIDs);

        if (features.contains(Feature.SENTENCES)) {
            logger.debug("Creating sentence hyperedges for document {}", document.getDocID());

            List<List<String>> sentenceTokens = analyzePerSentence(document.getText());
            Set<Integer> targetTermNodeIDs = new HashSet<>();

            for (List<String> tokens : sentenceTokens) {
                SentenceEdge sentenceEdge = new SentenceEdge();
                int sentenceEdgeID = getOrCreateUndirectedEdge(sentenceEdge);

                Set<Integer> targetSentenceTermNodeIDs = tokens.stream().map(token -> {
                    TermNode termNode = new TermNode(token);
                    return getOrCreateNode(termNode);
                }).collect(Collectors.toSet());
                addNodesToUndirectedHyperEdge(sentenceEdgeID, targetSentenceTermNodeIDs);

                targetTermNodeIDs.addAll(targetSentenceTermNodeIDs);
            }

            addNodesToUndirectedHyperEdge(documentEdgeID, targetTermNodeIDs);
        } else {
            List<String> tokens = analyze(document.getText());
            if (tokens.isEmpty()) return;

            Set<Integer> targetTermNodeIDs = tokens.stream().map(token -> {
                TermNode termNode = new TermNode(token);
                return getOrCreateNode(termNode);
            }).collect(Collectors.toSet());
            addNodesToUndirectedHyperEdge(documentEdgeID, targetTermNodeIDs);

            if (features.contains(Feature.TF_BINS)) {
                Map<Integer, Long> tf = tokens.stream().collect(Collectors.groupingBy(token -> {
                    TermNode termNode = new TermNode(token);
                    return getOrCreateNode(termNode);
                }, Collectors.counting()));

                /*Map<Integer, Long> sortedTF = tf.entrySet().stream().sorted(Map.Entry.comparingByValue())
                        .collect(Collectors.toMap(Map.Entry::getKey, Map.Entry::getValue,
                                (oldValue, newValue) -> oldValue, LinkedHashMap::new));*/

                double[] data = tf.values().stream().mapToDouble(Long::doubleValue).toArray();

                double left = Double.MIN_VALUE;
                double right = 0;
                for (int i = 1; i <= this.tfBins; i++) {
                    double percentile = 100d / this.tfBins * i;
                    float weight = (float) i / this.tfBins;

                    left = right;
                    right = StatUtils.percentile(data, percentile);

                    final double fLeft = left;
                    final double fRight = right;
                    Set<Integer> currentBinTermNodeIDs = tf.entrySet().stream()
                            .filter(e -> e.getValue() > fLeft && e.getValue() <= fRight).map(Map.Entry::getKey)
                            .collect(Collectors.toSet());


                    // System.out.println("Percentile: " + percentile + ", weight: " + weight + ", Interval: (" + left
                    //         + ", " + right + "]");

                    if (currentBinTermNodeIDs.isEmpty()) continue;

                    TFBinEdge tfBinEdge = new TFBinEdge();
                    int tfBinEdgeID = getOrCreateUndirectedEdge(tfBinEdge);
                    addNodesToUndirectedHyperEdge(tfBinEdgeID, currentBinTermNodeIDs);
                    // System.out.println("Doc: " + documentEdgeID + ", TFbin: " + tfBinEdgeID + ", Count: "
                    //         + currentBinTermNodeIDs.size());
                    edgeWeights.setValue(tfBinEdgeID, weight);
                }
            }
        }

        numDocs++;
    }

    private Set<Integer> indexEntitiesUsingDocumentCooccurrence(Document document) {
        Set<Node> nodes = new HashSet<>();

        for (Triple triple : document.getTriples()) {
            nodes.add(new EntityNode(triple.getSubject()));
            nodes.add(new EntityNode(triple.getObject()));
        }

        Set<Integer> nodeIDs = new HashSet<>();

        if (nodes.isEmpty()) return nodeIDs;

        Integer edgeID = null;
        if (!features.contains(Feature.SKIP_RELATED_TO)) {
            RelatedToEdge relatedToEdge = new RelatedToEdge();
            edgeID = createUndirectedEdge(relatedToEdge);
        }

        for (Node node : nodes) {
            int entityNodeID = getOrCreateNode(node);
            nodeIDs.add(entityNodeID);
            synchronized (this) {
                if (edgeID != null) graph.addToUndirectedHyperEdge(edgeID, entityNodeID);
            }
        }

        return nodeIDs;
    }

    // TODO could use directed hyperedges
    private Set<Integer> indexEntitiesUsingGroupingBySubject(Document document) {
        Set<Integer> nodeIDs = new HashSet<>();

        if (document.hasEntities()) {
            for (Entity entity : document.getEntities()) {
                EntityNode entityNode = new EntityNode(entity);
                nodeIDs.add(getOrCreateNode(entityNode));
            }
        }

        Map<EntityNode, Integer> edgeIDs = new HashMap<>();
        for (Triple triple : document.getTriples()) {
            EntityNode subjectNode = new EntityNode(triple.getSubject());
            EntityNode objectNode = new EntityNode(triple.getObject());
            int subjectNodeID = getOrCreateNode(subjectNode);
            int objectNodeID = getOrCreateNode(objectNode);

            if (!document.hasEntities()) {
                nodeIDs.add(subjectNodeID);
                nodeIDs.add(objectNodeID);
            }

            if (!features.contains(Feature.SKIP_RELATED_TO)) {
                Integer edgeID = edgeIDs.get(subjectNode);
                if (edgeID == null) {
                    edgeID = createUndirectedEdge(new RelatedToEdge());
                    edgeIDs.put(subjectNode, edgeID);
                }

                synchronized (this) {
                    graph.addToUndirectedHyperEdge(edgeID, this.nodeIndex.get(objectNode));
                }
            }
        }

        return nodeIDs;
    }

    private Set<Integer> indexEntities(Document document) {
        switch (this.entityIndexingStrategy) {
        case DOCUMENT_COOCCURRENCE:
            return indexEntitiesUsingDocumentCooccurrence(document);
        case GROUP_BY_SUBJECT:
            return indexEntitiesUsingGroupingBySubject(document);
        }

        return new HashSet<>();
    }

    private void linkTextAndKnowledge() {
        logger.info("Building trie from term nodes");
        Trie.TrieBuilder trieBuilder = Trie.builder().ignoreOverlaps().ignoreCase().onlyWholeWords();

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
                Set<Integer> termNodes = emits.stream().map(e -> nodeIndex.get(new TermNode(e.getKeyword())))
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
                        List<IWordID> senses = idxWord.getWordIDs();
                        IWordID wordID = senses.get(0);
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
                                synEdgeAux.put(edgeID, senses.size());
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

    private void linkContextuallySimilarTerms()
            throws IOException, ParseException, ParserConfigurationException, SAXException {
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

            FloatList embeddingSims = new FloatArrayList();
            if (nodeIndex.containsKey(termNode)) {
                ContextEdge contextEdge = new ContextEdge();
                int edgeID = createUndirectedEdge(contextEdge);
                this.graph.addToUndirectedHyperEdge(edgeID, nodeIndex.get(termNode));

                v.edges(Direction.BOTH, "edge").forEachRemaining(e -> {
                    Vertex source = e.bothVertices().next();
                    Vertex target = e.bothVertices().next();
                    Vertex other = source.property("name").value().equals(term) ? target : source;
                    Node otherNode = new TermNode((String) other.property("name").value());
                    this.graph.addToUndirectedHyperEdge(edgeID, getOrCreateNode(otherNode));

                    float weight = 1f;
                    if (e.property("weight").isPresent()) {
                        weight = (float) (double) e.property("weight").value();
                    }
                    embeddingSims.add(weight);
                });
                contextEdgeAux.put(edgeID, embeddingSims);
            }
        });
    }

    public void prepareAutocomplete() {
        logger.info("Preparing autocomplete trie");

        this.entityNameTrie = new PatriciaTrie<>();
        this.entityNameTrie.putAll(
            this.nodeIndex.keySet().stream()
                    .filter(n -> n instanceof EntityNode)
                    .collect(Collectors.toMap(Node::getName, Node::getName)));
    }

    public List<String> autocomplete(String substring) {
        if (this.entityNameTrie == null) {
            prepareAutocomplete();
        }

        List<String> matches = new ArrayList<>();

        matches.addAll(
            this.entityNameTrie
                .prefixMap(substring)
                .values()
                .stream()
                .limit(10)
                .collect(Collectors.toList()));

        return matches;
    }

    private float probalisticIDF(int numDocs, int numDocsWithTerm) {
        float probIDF = (float) Math.log10((float) (numDocs - numDocsWithTerm) / numDocsWithTerm);
        return Math.min(1, Math.max(0, probIDF));
    }

    private float linearIDF(int numDocs, int numDocsWithTerm) {
        return 1 - (float) numDocsWithTerm / numDocs;
    }

    private float sigmoidIDF(int numDocs, int numDocsWithTerm, float alpha) {
        return (float) (2 * sigmoid.value(alpha * (numDocs - numDocsWithTerm) / numDocsWithTerm) - 1);
    }

    private void computeNodeWeights() {
        logger.info("Computing node weights");
        for (int nodeID : graph.getVertices()) {
            Node node = nodeIndex.getKey(nodeID);
            if (node instanceof TermNode || node instanceof EntityNode) {
                int numDocsWithTerm = 0;
                for (int edgeID : graph.getEdgesIncidentTo(nodeID)) {
                    Edge edge = edgeIndex.getKey(edgeID);
                    if (edge instanceof DocumentEdge) {
                        numDocsWithTerm++;
                    }
                }
                nodeWeights.setValue(nodeID, sigmoidIDF(numDocs, numDocsWithTerm, (float) Math.pow(numDocs, -0.75)));
            }
        }
    }

    private float computeContainedInHyperEdgeWeight(int edgeID) {
        return 1f / graph.getDirectedHyperEdgeTail(edgeID).size();
    }

    private float computeRelatedToHyperEdgeWeight(int edgeID) {
        IntSet entityNodeIDs = graph.getUndirectedHyperEdgeVertices(edgeID);

        float weight = entityNodeIDs.parallelStream().map(entityNodeID -> {
            IntSet neighborNodeIDs = graph.getNeighbours(entityNodeID);
            neighborNodeIDs.retainAll(entityNodeIDs);
            neighborNodeIDs.remove(entityNodeID.intValue());
            return (float) neighborNodeIDs.size() / entityNodeIDs.size();
        }).reduce(0f, (a, b) -> a + b);

        weight /= entityNodeIDs.size();

        return weight;
    }

    private float computeSynonymHyperEdgeWeight(int edgeID) {
        if (synEdgeAux.containsKey(edgeID)) {
            return 1f / (float) synEdgeAux.get(edgeID);
        }
        return 1f;
    }

    private float computeContextHyperEdgeWeight(int edgeID) {
        return computeContextHyperEdgeWeight(edgeID, 0.5f);
    }

    private float computeContextHyperEdgeWeight(int edgeID, float min) {
        if (contextEdgeAux.containsKey(edgeID)) {
            FloatList embeddingSims = contextEdgeAux.get(edgeID);
            return (float) embeddingSims.stream().mapToDouble(sim -> (sim - min) / (1 - min)).average().orElse(0d);
        }
        return 1.0f;
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
                /*
                 * logger.warn("Using random weight for related-to edges (TESTING ONLY)"); edgeWeights.setValue(edgeID,
                 * (float) Math.random());
                 */
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

    // TODO also delete weights for removed nodes and egdes
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
        // createReachabilityIndex();
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
            logger.info("{} indexed documents in {} ({}/doc, {} docs/h)", counter, formatMillis(totalTime),
                    formatMillis(avgTimePerDocument), counter * 3600000 / totalTime);
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
            ObjectInputStream input = new DecompressibleInputStream(new FileInputStream(nodeIndexFile));
            this.nodeIndex = (BidiMap) input.readObject();
            input.close();
        } catch (ClassNotFoundException | IOException e) {
            logger.warn("Cannot read node index from {}", nodeIndexFile);
            return false;
        }

        File edgeIndexFile = new File(directory, "edge.idx");
        try {
            ObjectInputStream input = new DecompressibleInputStream(new FileInputStream(edgeIndexFile));
            this.edgeIndex = (BidiMap) input.readObject();
            input.close();
        } catch (ClassNotFoundException | IOException e) {
            logger.warn("Cannot read edge index from {}", edgeIndexFile);
            return false;
        }

        File reachabilityIndexFile = new File(directory, "reachability.idx");
        try {
            ObjectInputStream input = new DecompressibleInputStream(new FileInputStream(reachabilityIndexFile));
            this.reachabilityIndex = (Map) input.readObject();
            input.close();
        } catch (ClassNotFoundException | IOException e) {
            logger.warn("Cannot read  reachability index from {}", reachabilityIndexFile);
            return false;
        }

        File nodeWeightsFile = new File(directory, "node_weights.prp");
        try {
            ObjectInputStream input = new DecompressibleInputStream(new FileInputStream(nodeWeightsFile));
            this.nodeWeights = (NumericalProperty) input.readObject();
            input.close();
        } catch (ClassNotFoundException | IOException e) {
            logger.warn("Cannot read node weights from {}", nodeWeightsFile);
            return false;
        }

        File edgeWeightsFile = new File(directory, "edge_weights.prp");
        try {
            ObjectInputStream input = new DecompressibleInputStream(new FileInputStream(edgeWeightsFile));
            this.edgeWeights = (NumericalProperty) input.readObject();
            input.close();
        } catch (ClassNotFoundException | IOException e) {
            logger.warn("Cannot read edge weights from {}", edgeWeightsFile);
            return false;
        }

        File hypergraphFile = new File(directory, "hypergraph.graph");
        try {
            ObjectInputStream input = new DecompressibleInputStream(new FileInputStream(hypergraphFile));
            this.graph = (InMemoryGrph) input.readObject();
            this.graph.initAlgorithms();
            input.close();
        } catch (ClassNotFoundException | IOException e) {
            logger.warn("Cannot read hypergraph from {}", hypergraphFile);
            return false;
        }

        logger.info("Finished loading index from {}", directory.getAbsolutePath());

        return true;
    }

    public void unload() {
        this.nodeIndex = null;
        this.edgeIndex = null;
        this.reachabilityIndex = null;
        this.nodeWeights = null;
        this.edgeWeights = null;
        this.graph = null;
        System.gc();
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

    private IntSet getQueryEntityNodeIDs(List<String> entities) {
        IntSet entityNodes = new LucIntHashSet(10);

        for (String entity : entities) {
            EntityNode entityNode = new EntityNode(new Entity(entity));
            if (nodeIndex.containsKey(entityNode)) {
                entityNodes.add(nodeIndex.get(entityNode).intValue());
            }
        }

        return entityNodes;
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
        result.addAll(graph.getEdgesIncidentTo(sourceNodeID).stream().filter(edgeID -> {
            Edge edge = edgeIndex.getKey(edgeID);
            return edgeType.isInstance(edge);
        }).flatMap(edgeID -> {
            IntSet nodeIDs = new LucIntHashSet(10);
            if (graph.isDirectedHyperEdge(edgeID)) {
                nodeIDs.addAll(graph.getVerticesIncidentToEdge(edgeID));
            } else {
                nodeIDs.addAll(graph.getUndirectedHyperEdgeVertices(edgeID));
            }
            return nodeIDs.stream().filter(nodeID -> !nodeID.equals(sourceNodeID));
        }).collect(Collectors.toSet()));
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

        // if (neighborIDs.isEmpty()) return 0;

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

        List<grph.path.Path> paths = AllPaths
                .compute(entityNodeID, graph, SEARCH_MAX_DISTANCE, MAX_PATHS_PER_PAIR, false).stream()
                .flatMap(Collection::stream).filter(path -> path.containsVertex(seedNodeID))
                .collect(Collectors.toList());

        for (grph.path.Path path : paths) {
            perSeedScore += seedWeight * 1d / (1 + path.getLength());
        }
        perSeedScore /= 1 + paths.size();

        return perSeedScore;
    }

    private grph.path.Path randomWalk(int startNodeID, int length, boolean isDirected, boolean isBiased,
            int nodeFatigue, int edgeFatigue) {
        grph.path.Path path = new ArrayListPath();
        path.setSource(startNodeID);
        randomStep(startNodeID, length, path, isDirected, isBiased, nodeFatigue, edgeFatigue, 0);
        return path;
    }

    private void randomStep(int nodeID, int remainingSteps, grph.path.Path path, boolean isDirected, boolean isBiased,
            int nodeFatigue, int edgeFatigue, float restartProb) {
        if (remainingSteps == 0 || nodeFatigueStatus.containsKey(nodeID)) return;

        if (nodeFatigue > 0) {
            // Decrement fatigue for all nodes
            for (Iterator<Map.Entry<Integer, Integer>> it = nodeFatigueStatus.entrySet().iterator(); it.hasNext();) {
                Map.Entry<Integer, Integer> entry = it.next();
                if (entry.getValue() > 0) {
                    entry.setValue(entry.getValue() - 1);
                } else {
                    it.remove();
                }
            }
            // Set node fatigue for start node
            nodeFatigueStatus.put(nodeID, nodeFatigue);
        }

        if (edgeFatigue > 0) {
            // Decrement fatigue for all edges
            for (Iterator<Map.Entry<Integer, Integer>> it = edgeFatigueStatus.entrySet().iterator(); it.hasNext();) {
                Map.Entry<Integer, Integer> entry = it.next();
                if (entry.getValue() > 0) {
                    entry.setValue(entry.getValue() - 1);
                } else {
                    it.remove();
                }
            }
        }

        IntSet edgeIDs;
        if (isDirected) {
            edgeIDs = graph.getOutEdges(nodeID);
        } else {
            edgeIDs = graph.getEdgesIncidentTo(nodeID);
        }

        if (logger.isTraceEnabled()) {
            logger.trace("Selectable out edges for random step: {}", String.join(", ", edgeIDs.stream()
                    .map(edgeID -> ((Edge) edgeIndex.getKey(edgeID)).toString()).toArray(String[]::new)));
        }

        if (edgeIDs.isEmpty()) return;
        if (edgeFatigue > 0) {
            edgeIDs.removeAll(edgeFatigueStatus.keySet());
        }

        int randomEdgeID;
        if (isBiased) {
            Float[] edgeWeights = edgeIDs.stream().map(this.edgeWeights::getValueAsFloat).toArray(Float[]::new);
            randomEdgeID = sampleNonUniformlyAtRandom(edgeIDs.toIntArray(), ArrayUtils.toPrimitive(edgeWeights));
        } else {
            randomEdgeID = sampleUniformlyAtRandom(edgeIDs.toIntArray());
        }

        IntSet nodeIDs = new LucIntHashSet(10);
        if (graph.isDirectedHyperEdge(randomEdgeID)) {
            nodeIDs.addAll(graph.getDirectedHyperEdgeHead(randomEdgeID));
            if (!isDirected) nodeIDs.addAll(graph.getDirectedHyperEdgeTail(randomEdgeID));
        } else {
            nodeIDs.addAll(graph.getUndirectedHyperEdgeVertices(randomEdgeID));
            nodeIDs.remove(nodeID);
        }
        if (nodeFatigue > 0) {
            nodeIDs.removeAll(nodeFatigueStatus.keySet());
        }

        if (logger.isTraceEnabled()) {
            logger.trace("Selectable nodes for random step: {}",
                    String.join(", ",
                            nodeIDs.stream()
                                    .map(selectableNodeID -> ((Node) nodeIndex.getKey(selectableNodeID)).toString())
                                    .toArray(String[]::new)));
        }

        if (nodeIDs.isEmpty()) return;
        int randomNodeID;
        if (isBiased) {
            Float[] nodeWeights = nodeIDs.stream().map(this.nodeWeights::getValueAsFloat).toArray(Float[]::new);
            randomNodeID = sampleNonUniformlyAtRandom(nodeIDs.toIntArray(), ArrayUtils.toPrimitive(nodeWeights));
        } else {
            randomNodeID = sampleUniformlyAtRandom(nodeIDs.toIntArray());
        }

        path.extend(randomEdgeID, randomNodeID);
        randomStep(randomNodeID, remainingSteps - 1, path, isDirected, isBiased, nodeFatigue, edgeFatigue, restartProb);
    }

    public ResultSet hyperRankSearch(IntSet seedNodeIDs, Engine.Task task, float d, int n, boolean isWeighted,
            boolean useDegreeNormalization) {
        logger.info("Searching using HyperRank (d = {}, n = {}, weighted = {}, degree_normalization = {})", d, n,
                isWeighted, useDegreeNormalization);

        // An atom is either a node or a hyperedge (we follow the same nomenclature as HypergraphDB)
        Int2FloatOpenHashMap atomVisits = new Int2FloatOpenHashMap();

        trace.add("HyperRank (d = %.2f, n = {})", d, n);
        trace.goDown();

        int nodeID;
        if (isWeighted) {
            trace.add("Selecting start seed node non-uniformly at random");
            Float[] nodeWeights = seedNodeIDs.stream().map(this.nodeWeights::getValueAsFloat).toArray(Float[]::new);
            nodeID = sampleNonUniformlyAtRandom(seedNodeIDs.toIntArray(), ArrayUtils.toPrimitive(nodeWeights));
        } else {
            trace.add("Selecting start seed node uniformly at random");
            nodeID = sampleUniformlyAtRandom(seedNodeIDs.toIntArray());
        }

        for (int i = 0; i < n; i++) {
            if (task != Engine.Task.DOCUMENT_RETRIEVAL) {
                atomVisits.addTo(nodeID, 1);
            }

            IntSet edgeIDs = graph.getOutEdges(nodeID);

            // Teleport either by chance or if it's a sink.
            if (random() > d || edgeIDs.isEmpty()) {
                if (isWeighted) {
                    trace.add("Found a sink, teleporting non-uniformly at random to a seed node");
                    Float[] nodeWeights = seedNodeIDs.stream().map(this.nodeWeights::getValueAsFloat)
                            .toArray(Float[]::new);
                    nodeID = sampleNonUniformlyAtRandom(seedNodeIDs.toIntArray(), ArrayUtils.toPrimitive(nodeWeights));
                } else {
                    trace.add("Found a sink, teleporting uniformly at random to a seed node");
                    nodeID = sampleUniformlyAtRandom(seedNodeIDs.toIntArray());
                }
                continue;
            }

            int randomEdgeID;
            if (isWeighted) {
                Float[] edgeWeights = edgeIDs.stream().map(this.edgeWeights::getValueAsFloat).toArray(Float[]::new);
                randomEdgeID = sampleNonUniformlyAtRandom(edgeIDs.toIntArray(), ArrayUtils.toPrimitive(edgeWeights));
            } else {
                randomEdgeID = sampleUniformlyAtRandom(edgeIDs.toIntArray());
            }

            if (task == Engine.Task.DOCUMENT_RETRIEVAL) {
                atomVisits.addTo(randomEdgeID, 1);
            }

            IntSet nodeIDs = new LucIntHashSet(10);
            if (graph.isDirectedHyperEdge(randomEdgeID)) {
                nodeIDs.addAll(graph.getDirectedHyperEdgeHead(randomEdgeID));
            } else {
                nodeIDs.addAll(graph.getUndirectedHyperEdgeVertices(randomEdgeID));
                nodeIDs.remove(nodeID);
            }

            // This should never happen, but just in case.
            if (nodeIDs.isEmpty()) {
                continue;
            }

            if (isWeighted) {
                Float[] nodeWeights = nodeIDs.stream().map(this.nodeWeights::getValueAsFloat).toArray(Float[]::new);
                nodeID = sampleNonUniformlyAtRandom(nodeIDs.toIntArray(), ArrayUtils.toPrimitive(nodeWeights));
            } else {
                nodeID = sampleUniformlyAtRandom(nodeIDs.toIntArray());
            }
        }

        ResultSet resultSet = new ResultSet();
        resultSet.setTrace(trace);

        for (int atomID : atomVisits.keySet()) {
            Atom atom = task == Engine.Task.DOCUMENT_RETRIEVAL ? edgeIndex.getKey(atomID) : nodeIndex.getKey(atomID);
            trace.add(atom.toString().replace("%", "%%"));
            trace.goDown();
            trace.add("score = %f", atomVisits.get(atomID));
            trace.goUp();

            if (task == Engine.Task.DOCUMENT_RETRIEVAL && !(atom instanceof DocumentEdge)) continue;
            if (task == Engine.Task.ENTITY_RETRIEVAL && !(atom instanceof EntityNode)) continue;
            if (task == Engine.Task.TERM_RETRIEVAL && !(atom instanceof TermNode)) continue;

            if (atom instanceof RankableAtom) {
                RankableAtom rankableAtom = (RankableAtom) atom;
                logger.debug("Ranking atom {} using RANDOM_WALK_SCORE", rankableAtom);

                double norm = 1;
                if (useDegreeNormalization) {
                    norm = task == Engine.Task.DOCUMENT_RETRIEVAL ? graph.getEdgeDegree(atomID)
                            : graph.getVertexDegree(atomID);
                }

                // Unnormalized HyperRank (with or without degree normalization,
                // similar to document length normalization)
                double score = atomVisits.get(atomID) / norm;

                resultSet.addResult(
                        new Result(score, rankableAtom.getID(), rankableAtom.getName(), rankableAtom.getLabel()));
            }
        }

        if (atomVisits.isEmpty()) {
            trace.add(Trace.EMPTY);
        }

        trace.goUp();

        // Note: actually collecting is done in the previous block of code.
        trace.add("Collecting results (task=%s)", task);
        trace.goDown();

        for (Result result : resultSet) {
            trace.add(result == null || result.getName() == null ? "NULL" : result.getName());
            trace.goDown();
            trace.add("score = %f", result.getScore());
            trace.add("id= %s", result.getID());
            trace.add("name = %s", result.getName());
            trace.add("type = %s", result.getType());
            trace.goUp();
        }

        if (resultSet.isEmpty()) {
            trace.add(Trace.EMPTY);
        }

        return resultSet;
    }

    public ResultSet randomWalkSearch(IntSet seedNodeIDs, Map<Integer, Double> seedNodeWeights, Engine.Task task,
            int walkLength, int walkRepeats, int nodeFatigue, int edgeFatigue, boolean isDirected, boolean isWeighted) {
        logger.info(
                "Searching using Random Walk Score (l = {}, r = {}, nf = {}, ef = {}, directed = {}, weighted = {})",
                walkLength, walkRepeats, nodeFatigue, edgeFatigue, isDirected, isWeighted);

        // An atom is either a node or a hyperedge (we follow the same nomenclature as HypergraphDB)
        Int2FloatOpenHashMap weightedAtomVisitProbability = new Int2FloatOpenHashMap();
        Int2DoubleOpenHashMap atomCoverage = new Int2DoubleOpenHashMap();

        trace.add("Random Walk Score (l = %d, r = %d, nf = %d, ef = {})", walkLength, walkRepeats, nodeFatigue,
                edgeFatigue);
        trace.goDown();
        trace.add("Tracing system disabling required for parallel computing blocks");

        seedNodeIDs.parallelStream().forEach(seedNodeID -> {
            Int2IntOpenHashMap atomVisits = new Int2IntOpenHashMap();
            /*trace.add("From seed node %s", nodeIndex.getKey(seedNodeID));
            trace.goDown();*/

            for (int i = 0; i < walkRepeats; i++) {
                grph.path.Path randomPath = randomWalk(seedNodeID, walkLength, isDirected, isWeighted, nodeFatigue,
                        edgeFatigue);

                StringBuilder messageRandomPath = new StringBuilder();
                for (int j = 0; j < randomPath.getNumberOfVertices(); j++) {
                    if (j > 0) {
                        messageRandomPath.append(" -> ")
                                .append(edgeIndex.getKey(randomPath.getEdgeHeadingToVertexAt(j)).toString())
                                .append(" -> ");
                    }
                    messageRandomPath.append(nodeIndex.getKey(randomPath.getVertexAt(j)).toString());
                }
                //trace.add(messageRandomPath.toString().replace("%", "%%"));
                // trace.goDown();

                for (int j = 0; j < randomPath.getNumberOfVertices(); j++) {
                    if (task == Engine.Task.DOCUMENT_RETRIEVAL) {
                        if (j > 0) {
                            atomVisits.addTo(randomPath.getEdgeHeadingToVertexAt(j), 1);
                        }
                    } else {
                        atomVisits.addTo(randomPath.getVertexAt(j), 1);
                        // trace.add("Node %s visited %d times", nodeIndex.getKey(nodeID), nodeVisits.get(nodeID));
                    }

                    if (logger.isTraceEnabled()) {
                        if (j > 0) {
                            logger.trace("Hyperedge in random path: {}",
                                    edgeIndex.getKey(randomPath.getEdgeHeadingToVertexAt(j)).toString());
                        }
                        logger.trace("Node in random path: {}", nodeIndex.getKey(randomPath.getVertexAt(j)).toString());
                    }
                }

                // trace.goUp();
            }

            //trace.goUp();

            int maxVisits = Arrays.stream(atomVisits.values().toIntArray()).max().orElse(0);
            //trace.add("max(visits from seed node %s) = %d", nodeIndex.getKey(seedNodeID), maxVisits);

            /*
             * for (Map.Entry<Integer, Integer> entry : atomVisits.int2IntEntrySet()) {
             * System.out.println(nodeIndex.getKey(entry.getKey()).toString() + " -> " + entry.getValue()); }
             */

            /*
             * trace.add("Accumulating visit probability, weighted by seed node confidence"); trace.goDown();
             */
            for (int atomID : atomVisits.keySet()) {
                synchronized (this) {
                    atomCoverage.addTo(atomID, 1);
                    weightedAtomVisitProbability.compute(atomID,
                            (k, v) -> (v == null ? 0 : v) + (float) atomVisits.get(atomID) / maxVisits
                                    * seedNodeWeights.getOrDefault(seedNodeID, 1d).floatValue());
                }
                /*
                 * trace.add("score(%s) += visits(%s) * w(%s)", nodeIndex.getKey(nodeID), nodeIndex.getKey(nodeID),
                 * nodeIndex.getKey(seedNodeID)); trace.goDown(); trace.add("P(visit(%s)) = %f",
                 * nodeIndex.getKey(nodeID).toString(), (float) nodeVisits.get(nodeID) / maxVisits);
                 * trace.add("w(%s) = %f", nodeIndex.getKey(seedNodeID), seedNodeWeights.getOrDefault(seedNodeID, 1d));
                 * trace.add("score(%s) = %f", nodeIndex.getKey(nodeID), weightedNodeVisitProbability.get(nodeID));
                 * trace.goUp();
                 */
            }

            /*
             * trace.add("%d visited nodes", atomVisits.size()); trace.goUp();
             */

            /*
             * trace.goUp(); trace.goUp();
             */
        });

        trace.goUp();

        ResultSet resultSet = new ResultSet();
        resultSet.setTrace(trace);

        double maxCoverage = Arrays.stream(atomCoverage.values().toDoubleArray()).max().orElse(0d);

        trace.add("Weighted nodes [max(coverage) = %f]", maxCoverage);
        trace.goDown();

        for (int atomID : weightedAtomVisitProbability.keySet()) {
            atomCoverage.compute(atomID, (k, v) -> v / maxCoverage);

            Atom atom = task == Engine.Task.DOCUMENT_RETRIEVAL ? edgeIndex.getKey(atomID) : nodeIndex.getKey(atomID);
            trace.add(atom.toString().replace("%", "%%"));
            trace.goDown();
            trace.add("score = %f", weightedAtomVisitProbability.get(atomID));
            trace.add("coverage = %f", atomCoverage.get(atomID));
            trace.goUp();

            if (task == Engine.Task.DOCUMENT_RETRIEVAL && !(atom instanceof DocumentEdge)) continue;
            if (task == Engine.Task.ENTITY_RETRIEVAL && !(atom instanceof EntityNode)) continue;
            if (task == Engine.Task.TERM_RETRIEVAL && !(atom instanceof TermNode)) continue;

            if (atom instanceof RankableAtom) {
                RankableAtom rankableAtom = (RankableAtom) atom;
                logger.debug("Ranking atom {} using RANDOM_WALK_SCORE", rankableAtom);

                // Random Walk Score
                double score = atomCoverage.get(atomID) * weightedAtomVisitProbability.get(atomID);

                // if (score > PROBABILITY_THRESHOLD) {
                resultSet.addResult(
                        new Result(score, rankableAtom.getID(), rankableAtom.getName(), rankableAtom.getLabel()));
                // }
            }
        }

        if (weightedAtomVisitProbability.isEmpty()) {
            trace.add(Trace.EMPTY);
        }

        trace.goUp();

        trace.add("Collecting results (task=%s)", task);
        trace.goDown();

        for (Result result : resultSet) {
            trace.add(result == null || result.getName() == null ? "NULL" : result.getName());
            trace.goDown();
            trace.add("score = %f", result.getScore());
            trace.add("id= %s", result.getID());
            trace.add("name = %s", result.getName());
            trace.add("type = %s", result.getType());
            trace.goUp();
        }

        if (resultSet.isEmpty()) {
            trace.add(Trace.EMPTY);
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

    /*
     * private Set<Node> getNeighborhood(Node node, int depth) { return getNeighborhood(node, depth, new HashSet<>()); }
     *
     * private Set<Node> getNeighborhood(Node node, int depth, Set<Node> visited) { visited.add(node);
     *
     * Set<Node> neighborhood = new HashSet<>();
     *
     * if (depth == 0) return neighborhood;
     *
     * Collection<Node> neighbors = graph.getUndirectedNeighborsPerEdgeType(node); neighborhood.addAll(neighbors);
     *
     * for (Node neighbor : neighbors) { if (visited.contains(neighbor)) continue;
     * neighborhood.addAll(getNeighborhood(neighbor, depth - 1, visited)); }
     *
     * return neighborhood; }
     */

    /*
     * public void updateQuerySubgraph(Set<Node> queryTermNodes) { logger.info("Updating query subgraph"); Set<Node>
     * nodes = new HashSet<>(); for (Node queryTermNode : queryTermNodes) { nodes.addAll(getNeighborhood(queryTermNode,
     * 0)); } System.out.println(this.graph.getVertexCount() + " : " + this.graph.getEdgeCount()); this.graph =
     * FilterUtils.createInducedSubgraph(nodes, graph); System.out.println(this.graph.getVertexCount() + " : " +
     * this.graph.getEdgeCount()); }
     */

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

    public ResultSet entityIteratorSearch(IntSet seedNodeIDs, Map<Integer, Double> seedNodeWeights, Engine.Task task,
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

                if (score > 0) {
                    synchronized (this) {
                        // resultSet.addReplaceResult(new Result(score, entityNode));
                        resultSet.addResult(new Result(score, entityNode.getID(), entityNode.getName(), "entity"));
                    }
                }
            }
        });

        return resultSet;
    }

    @Override
    public ResultSet search(String query, int offset, int limit) throws IOException {
        return search(query, offset, limit, Engine.QueryType.KEYWORD_QUERY, Engine.Task.DOCUMENT_RETRIEVAL);
    }

    public ResultSet search(String query, int offset, int limit, Engine.QueryType queryType, Engine.Task task) throws IOException {
        Map<String, String> params = new HashMap<>();
        params.put("l", String.valueOf(DEFAULT_WALK_LENGTH));
        params.put("r", String.valueOf(DEFAULT_WALK_REPEATS));
        return search(query, offset, limit, queryType, task, RankingFunction.RANDOM_WALK_SCORE, params, false);
    }

    public ResultSet search(String query, int offset, int limit, Engine.QueryType queryType, Engine.Task task,
            RankingFunction function, Map<String, String> params, boolean debug) throws IOException {
        long start = System.currentTimeMillis();

        trace.reset();
        trace.setEnabled(debug);

        boolean useQueryExpansion = Boolean.valueOf(params.getOrDefault("expansion", "false"));

        List<String> tokens;
        IntSet queryNodeIDs;
        if (queryType == Engine.QueryType.ENTITY_QUERY) {
            logger.info("Query type: entity query");
            tokens = Arrays.stream(query.split("\\|\\|"))
                    .map(String::trim)
                    .collect(Collectors.toList());
            queryNodeIDs = getQueryEntityNodeIDs(tokens);
            if (useQueryExpansion) {
                logger.warn("Query expansion is not supported for entity queries");
                useQueryExpansion = false;
            }
        } else {
            logger.info("Query type: keyword query");
            tokens = analyze(query);
            queryNodeIDs = getQueryTermNodeIDs(tokens);
        }

        logger.info("Found {} query nodes found for [ {} ]", queryNodeIDs.size(), query);
        trace.add("Mapping query terms/entities [ %s ] to query term/entity nodes", StringUtils.join(tokens, ", "));
        trace.goDown();
        for (int queryNodeID : queryNodeIDs) {
            trace.add(nodeIndex.getKey(queryNodeID).toString());
        }
        trace.goUp();

        IntSet seedNodeIDs = null;
        Map<Integer, Double> seedNodeWeights = null;

        if (useQueryExpansion) {
            seedNodeIDs = getSeedNodeIDs(queryNodeIDs);
            // System.out.println("Seed Nodes: " + seedNodeIDs.stream().map(nodeID -> nodeID + "=" +
            // nodeIndex.getKey(nodeID).toString()).collect(Collectors.toList()));
            trace.add("Mapping query term nodes to seed nodes");
            trace.goDown();
            for (int seedNodeID : seedNodeIDs) {
                trace.add(nodeIndex.getKey(seedNodeID).toString().replace("%", "%%"));
            }
            trace.goUp();

            seedNodeWeights = seedNodeConfidenceWeights(seedNodeIDs, queryNodeIDs);
            // System.out.println("Seed Node Confidence Weights: " + seedNodeWeights);
            logger.info("Expanded [ {} ] to {} weighted seed nodes", query, seedNodeWeights.size());
            trace.add("Calculating confidence weight for seed nodes");
            trace.goDown();
            for (Map.Entry<Integer, Double> entry : seedNodeWeights.entrySet()) {
                trace.add("w(%s) = %f", nodeIndex.getKey(entry.getKey()), entry.getValue());
            }
            trace.goUp();
        }

        ResultSet resultSet;
        switch (function) {
        case HYPERRANK:
            resultSet = hyperRankSearch(useQueryExpansion ? seedNodeIDs : queryNodeIDs, task,
                    Float.valueOf(params.getOrDefault("d", String.valueOf(DEFAULT_DAMPING_FACTOR))),
                    Integer.valueOf(params.getOrDefault("n", String.valueOf(DEFAULT_MAX_ITERATIONS))),
                    Boolean.valueOf(params.getOrDefault("weighted", "false")),
                    Boolean.valueOf(params.getOrDefault("norm", "false")));
            break;
        case RANDOM_WALK_SCORE:
            resultSet = randomWalkSearch(useQueryExpansion ? seedNodeIDs : queryNodeIDs,
                    useQueryExpansion ? seedNodeWeights : new HashMap<>(), task,
                    Integer.valueOf(params.getOrDefault("l", String.valueOf(DEFAULT_WALK_LENGTH))),
                    Integer.valueOf(params.getOrDefault("r", String.valueOf(DEFAULT_WALK_REPEATS))),
                    Integer.valueOf(params.getOrDefault("nf", String.valueOf(DEFAULT_FATIQUE))),
                    Integer.valueOf(params.getOrDefault("ef", String.valueOf(DEFAULT_FATIQUE))),
                    Boolean.valueOf(params.getOrDefault("directed", "true")),
                    Boolean.valueOf(params.getOrDefault("weighted", "false")));
            break;
        case ENTITY_WEIGHT:
        case JACCARD_SCORE:
            resultSet = entityIteratorSearch(seedNodeIDs, seedNodeWeights, task, function);
            break;
        default:
            logger.warn("Ranking function {} is unsupported", function);
            resultSet = ResultSet.empty();
        }

        long end = System.currentTimeMillis();

        logger.info("{} results retrieved for [ {} ] in {}ms", resultSet.getNumDocs(), query, end - start);
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
            nodeCountPerType.compute(nodeIndex.getKey(nodeID).getClass().getSimpleName(), (k, v) -> {
                if (v == null)
                    v = 1;
                else
                    v += 1;
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

            directedEdgeCountPerType.compute(edgeIndex.getKey(edgeID).getClass().getSimpleName(), (k, v) -> {
                if (v == null)
                    v = 1;
                else
                    v += 1;
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

            undirectedEdgeCountPerType.compute(edgeIndex.getKey(edgeID).getClass().getSimpleName(), (k, v) -> {
                if (v == null)
                    v = 1;
                else
                    v += 1;
                return v;
            });
        }

        for (Map.Entry<String, Integer> entry : undirectedEdgeCountPerType.entrySet()) {
            summary.add("%10d %s", entry.getValue(), entry.getKey());
        }

        return summary;
    }

    /**
     * How many synonyms (i.e., terms in the tail of a SynonymEdge) link terms in two or more documents? How many
     * distinct documents on average do synonym terms link?
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
                            // Obtain term node document hyperedges
                            for (int docEdgeID : graph.getEdgesIncidentTo(neighborNodeID)) {
                                Edge docEdge = edgeIndex.getKey(docEdgeID);
                                if (docEdge instanceof DocumentEdge) {
                                    baseToDocs.computeIfAbsent(baseTermNodeID,
                                            k -> new HashSet<>(Collections.singletonList(docEdgeID)));
                                    baseToDocs.computeIfPresent(baseTermNodeID, (k, v) -> {
                                        v.add(docEdgeID);
                                        return v;
                                    });
                                }
                            }
                        }
                    }
                }
            }
        }

        long pathsBetweenDocs = baseToDocs.entrySet().stream().filter(entry -> entry.getValue().size() > 1).count();

        summary.add("%10d paths established between documents", pathsBetweenDocs);

        IntSummaryStatistics statsLinkedDocsPerEdgeType = baseToDocs.values().stream().mapToInt(Set::size)
                .summaryStatistics();

        summary.add("%10.2f documents linked on average per %s", statsLinkedDocsPerEdgeType.getAverage(), edgeTypeStr);
        summary.goDown();
        summary.add("%10d minimum documents linked per %s", statsLinkedDocsPerEdgeType.getMin(), edgeTypeStr);
        summary.add("%10d maximum documents linked per %s", statsLinkedDocsPerEdgeType.getMax(), edgeTypeStr);

        return summary;
    }

    public Trace getNodeList() {
        Trace summary = new Trace("Nodes");

        Class[] nodeClasses = { TermNode.class, EntityNode.class };

        for (Class nodeClass : nodeClasses) {
            summary.add(nodeClass.getSimpleName());
            summary.goDown();

            for (int nodeID : graph.getVertices()) {
                Node node = nodeIndex.getKey(nodeID);
                if (nodeClass.isInstance(node)) {
                    double nodeWeight = nodeWeights.getValueAsFloat(nodeID);
                    summary.add("%10d %.4f %s", nodeID, nodeWeight, node.getName());
                }
            }

            summary.goUp();
        }

        return summary;
    }

    public Trace getHyperedgeList() {
        Trace summary = new Trace("Hyperedges");

        Class[] hyperedgeClasses = { DocumentEdge.class, RelatedToEdge.class, ContainedInEdge.class };

        for (Class edgeClass : hyperedgeClasses) {
            summary.add(edgeClass.getSimpleName());
            summary.goDown();

            for (int edgeID : graph.getEdges()) {
                Edge edge = edgeIndex.getKey(edgeID);

                if (edgeClass.isInstance(edge)) {
                    float edgeWeight = edgeWeights.getValueAsFloat(edgeID);

                    if (graph.isDirectedHyperEdge(edgeID)) {
                        Set<String> tail = graph.getDirectedHyperEdgeTail(edgeID).stream()
                                .map(nodeID -> nodeIndex.getKey(nodeID).getName()).collect(Collectors.toSet());

                        Set<String> head = graph.getDirectedHyperEdgeHead(edgeID).stream()
                                .map(nodeID -> nodeIndex.getKey(nodeID).getName()).collect(Collectors.toSet());

                        summary.add("%10d %.4f %s -> %s", edgeID, edgeWeight, tail, head);
                    } else {
                        Set<String> nodes = graph.getUndirectedHyperEdgeVertices(edgeID).stream()
                                .map(nodeID -> nodeIndex.getKey(nodeID).getName()).collect(Collectors.toSet());
                        summary.add("%10d %.4f %s", edgeID, edgeWeight, nodes);
                    }
                }
            }

            summary.goUp();
        }

        return summary;
    }

    public InMemoryGrph toBipartiteGraph() {
        logger.info("Converting hypergraph to bipartite graph");

        InMemoryGrph g = new InMemoryGrph();

        for (IntCursor nodeCursor : IntCursor.fromFastUtil(graph.getVertices())) {
            g.addVertex(nodeCursor.value);
        }

        for (IntCursor edgeCursor : IntCursor.fromFastUtil(graph.getEdges())) {
            int connectorNode = g.getNextVertexAvailable();

            if (graph.isDirectedHyperEdge(edgeCursor.value)) {
                for (int source : graph.getDirectedHyperEdgeTail(edgeCursor.value)) {
                    g.addDirectedSimpleEdge(source, connectorNode);

                }

                for (int target : graph.getDirectedHyperEdgeHead(edgeCursor.value)) {
                    g.addDirectedSimpleEdge(connectorNode, target);
                }
            } else {
                for (int source : graph.getUndirectedHyperEdgeVertices(edgeCursor.value)) {
                    g.addUndirectedSimpleEdge(source, connectorNode);
                }
            }
        }

        return g;
    }

    public void exportWordNetNounSynsDistr(String workdir) throws IOException {
        String now = isoDateFormat.format(new Date());

        Path path = Paths.get(workdir, String.format("wordnet-noun-syns-distr-%s.csv", now));
        logger.info("Saving WordNet noun synonyms distribution to {}", path);
        try (BufferedWriter writer = Files.newBufferedWriter(path);
                CSVPrinter csvPrinter = new CSVPrinter(writer, CSVFormat.DEFAULT.withHeader("Word", "SynsCount"))) {
            IRAMDictionary dict = null;
            try {
                dict = new RAMDictionary(new File("/usr/share/wordnet"), ILoadPolicy.NO_LOAD);
                dict.open();

                Iterator<IIndexWord> it=dict.getIndexWordIterator(POS.NOUN);

                while (it.hasNext()) {
                    IIndexWord idxWord = it.next();
                    List<IWordID> senses = idxWord.getWordIDs();
                    IWordID wordID = senses.get(0);
                    IWord word = dict.getWord(wordID);
                    ISynset synset = word.getSynset();

                    csvPrinter.printRecord(word.getLemma(), synset.getWords().size());
                }
                csvPrinter.flush();
            } catch (IOException e) {
                logger.error(e.getMessage(), e);
            } finally {
                if (dict != null) {
                    dict.close();
                }
            }
        }
    }

    public void exportNodeWeights(String workdir) throws IOException {
        String now = isoDateFormat.format(new Date());

        Path path = Paths.get(workdir, String.format("node-weights-%s.csv", now));
        logger.info("Saving node weights to {}", path);
        try (BufferedWriter writer = Files.newBufferedWriter(path);
                CSVPrinter csvPrinter = new CSVPrinter(writer,
                        CSVFormat.DEFAULT.withHeader("Node ID", "Type", "Weight"))) {
            for (int nodeID : graph.getVertices()) {
                csvPrinter.printRecord(nodeID, nodeIndex.getKey(nodeID).getClass().getSimpleName(),
                        nodeWeights.getValueAsFloat(nodeID));
            }
            csvPrinter.flush();
        }
    }

    public void exportEdgeWeights(String workdir) throws IOException {
        String now = isoDateFormat.format(new Date());

        Path path = Paths.get(workdir, String.format("edge-weights-%s.csv", now));
        logger.info("Saving edge weights to {}", path);
        try (BufferedWriter writer = Files.newBufferedWriter(path);
                CSVPrinter csvPrinter = new CSVPrinter(writer,
                        CSVFormat.DEFAULT.withHeader("Edge ID", "Type", "Weight"))) {
            for (int edgeID : graph.getEdges()) {
                csvPrinter.printRecord(edgeID, edgeIndex.getKey(edgeID).getClass().getSimpleName(),
                        edgeWeights.getValueAsFloat(edgeID));
            }
            csvPrinter.flush();
        }
    }

    public int getDirectedInVertexDegree(int v) {
        LucIntSet inEdges = graph.getInOnlyEdges(v);
        int indegree = 0;

        for (IntCursor c : IntCursor.fromFastUtil(inEdges)) {
            int e = c.value;

            if (graph.isDirectedHyperEdge(e)) {
                indegree += graph.getDirectedHyperEdgeTail(e).size();
            }
        }

        return indegree;
    }

    public int getDirectedOutVertexDegree(int v) {
        LucIntSet outEdges = graph.getOutOnlyEdges(v);
        int outdegree = 0;

        for (IntCursor c : IntCursor.fromFastUtil(outEdges)) {
            int e = c.value;

            if (graph.isDirectedHyperEdge(e)) {
                outdegree += graph.getDirectedHyperEdgeHead(e).size();
            }
        }

        return outdegree;
    }

    public int getDirectedInEdgeDegree(int v) {
        return graph.getInOnlyEdges(v).size();
    }

    public int getDirectedOutEdgeDegree(int v) {
        return graph.getOutOnlyEdges(v).size();
    }

    public void exportNodeDegree(String workdir) throws IOException {
        String now = isoDateFormat.format(new Date());

        Path path = Paths.get(workdir, String.format("node-degree-%s.csv", now));
        logger.info("Saving node degrees to {}", path);
        try (BufferedWriter writer = Files.newBufferedWriter(path);
                CSVPrinter csvPrinter = new CSVPrinter(writer,
                        CSVFormat.DEFAULT.withHeader(
                            "NodeID", "Type", "Name", "VertexDegree", "EdgeDegree", "InVertexDegree", "OutVertexDegree",
                            "InEdgeDegree", "OutEdgeDegree", "DirectedInVertexDegree", "DirectedOutVertexDegree",
                            "DirectedInEdgeDegree", "DirectedOutEdgeDegree"))) {
            for (IntCursor nodeCursor : IntCursor.fromFastUtil(graph.getVertices())) {
                Node node = nodeIndex.getKey(nodeCursor.value);

                csvPrinter.printRecord(
                    nodeCursor.value,
                    node.getClass().getSimpleName(),
                    node.getName(),
                    graph.getVertexDegree(nodeCursor.value),
                    graph.getEdgeDegree(nodeCursor.value),
                    graph.getInVertexDegree(nodeCursor.value),
                    graph.getOutVertexDegree(nodeCursor.value),
                    graph.getInEdgeDegree(nodeCursor.value),
                    graph.getOutEdgeDegree(nodeCursor.value),
                    getDirectedInVertexDegree(nodeCursor.value),
                    getDirectedOutVertexDegree(nodeCursor.value),
                    getDirectedInEdgeDegree(nodeCursor.value),
                    getDirectedOutEdgeDegree(nodeCursor.value));
            }
            csvPrinter.flush();
        }
    }

    public void exportEdgeCardinality(String workdir) throws IOException {
        String now = isoDateFormat.format(new Date());

        Path path = Paths.get(workdir, String.format("edge-cardinality-%s.csv", now));
        logger.info("Saving edge degrees to {}", path);
        try (BufferedWriter writer = Files.newBufferedWriter(path);
                CSVPrinter csvPrinter = new CSVPrinter(writer,
                        CSVFormat.DEFAULT.withHeader(
                            "EdgeID", "Type", "IsDirected", "Cardinality", "UndirectedCardinality",
                            "TailCardinality", "HeadCardinality"))) {
            for (IntCursor edgeCursor : IntCursor.fromFastUtil(graph.getEdges())) {
                int undirectedCardinality = graph.isUndirectedHyperEdge(edgeCursor.value) ?
                    graph.getUndirectedHyperEdgeVertices(edgeCursor.value).size() : 0;

                int tailCardinality = graph.isDirectedHyperEdge(edgeCursor.value) ?
                    graph.getDirectedHyperEdgeTail(edgeCursor.value).size() : 0;

                int headCardinality = graph.isDirectedHyperEdge(edgeCursor.value) ?
                    graph.getDirectedHyperEdgeHead(edgeCursor.value).size() : 0;

                csvPrinter.printRecord(
                    edgeCursor.value,
                    edgeIndex.getKey(edgeCursor.value).getClass().getSimpleName(),
                    graph.isDirectedHyperEdge(edgeCursor.value),
                    undirectedCardinality + tailCardinality + headCardinality,
                    undirectedCardinality,
                    tailCardinality,
                    headCardinality);
            }
            csvPrinter.flush();
        }
    }

    /**
     * Estimate shortest distances between pairs of random nodes using intersecting random walks.
     *
     * Two random nodes are selected and a random walker is launched for either node. If the paths intersect,
     * then there is a path between the two nodes. We trim the paths after and before the first intersecting node,
     * respectively, and joint the two segments to form a path between the two nodes. We repeat this process several
     * times for the same pair of nodes, and then over multiple combinations of nodes.
     */
    public int[] estimateShortestDistances(int numNodePairs, int walkLength, int walkRepeats) {
        logger.info("Randomly selecting start and corresponding end nodes");

        int[] startNodeIDs = new int[numNodePairs];
        int[] endNodeIDs = new int[numNodePairs];

        for (int i = 0; i < numNodePairs; i++) {
            startNodeIDs[i] = sampleUniformlyAtRandom(graph.getVertices().toIntArray());
            endNodeIDs[i] = sampleUniformlyAtRandom(graph.getVertices().toIntArray());
        }

        int[] shortestDistances = IntStream.range(0, numNodePairs).map(i -> {
            logger.info("Processing {} walk repeats for node pair {} out of {}", walkRepeats, i+1, numNodePairs);

            int shortestDistance = IntStream.range(0, walkRepeats).parallel().map(j -> {
                Integer distance = null;

                grph.path.Path startPath = randomWalk(startNodeIDs[i], walkLength, false, false, 0, 0);
                grph.path.Path endPath = randomWalk(endNodeIDs[i], walkLength, false, false, 0, 0);

                if (distance == null && (startPath.getLength() > 0 || endPath.getLength() > 0)) {
                    distance = 0;
                }

                Integer firstCommonNodeID = null;
                IntSet endPathNodes = endPath.toVertexSet();

                for (int k = 0; k < startPath.getNumberOfVertices(); k++) {
                    distance++;
                    if (endPathNodes.contains(startPath.getVertexAt(k))) {
                        firstCommonNodeID = startPath.getVertexAt(k);
                        break;
                    }
                }

                if (firstCommonNodeID != null) {
                    boolean foundFirstCommonNode = false;
                    for (int k = 0; k < endPath.getNumberOfVertices(); k++) {
                        if (foundFirstCommonNode) {
                            distance++;
                        }

                        if (!foundFirstCommonNode && endPath.getVertexAt(k) == firstCommonNodeID) {
                            foundFirstCommonNode = true;
                        }
                    }
                }

                return distance;
            }).min().getAsInt();

            return shortestDistance;
        }).toArray();

        return shortestDistances;
    }

    public float estimateClusteringCoefficient(int numStartNodes, int numNeighbors) {
        logger.info("Sampling {} nodes uniformly at random", numStartNodes);
        int[] startNodeIDs = new int[numStartNodes];
        for (int i = 0; i < numStartNodes; i++) {
            startNodeIDs[i] = sampleUniformlyAtRandom(graph.getVertices().toIntArray());
        }

        logger.info("Computing two-node clustering coefficient for {} sampled neighbors", numNeighbors);

        return Arrays.stream(startNodeIDs).mapToObj(startNodeID -> {
            IntSet startNodeEdgeIDs = graph.getEdgesIncidentTo(startNodeID);

            int[] neighborIDs = graph.getNeighbours(startNodeID).toIntArray();
            IntArrays.shuffle(neighborIDs, new Random());

            return Arrays.stream(IntArrays.trim(neighborIDs, numNeighbors)).parallel().mapToObj(neighborID -> {
                IntSet neighborEdgeIDs = graph.getEdgesIncidentTo(neighborID);

                IntSet commonEdgeIDs = new LucIntHashSet(startNodeEdgeIDs.size());
                commonEdgeIDs.addAll(startNodeEdgeIDs);
                commonEdgeIDs.retainAll(neighborEdgeIDs);

                IntSet allEdgeIDs = new LucIntHashSet(startNodeEdgeIDs.size() + neighborEdgeIDs.size());
                allEdgeIDs.addAll(startNodeEdgeIDs);
                allEdgeIDs.addAll(neighborEdgeIDs);

                return new ClusteringCoefficientAccumulator((float) commonEdgeIDs.size() / allEdgeIDs.size());
            }).reduce(new ClusteringCoefficientAccumulator(),
                    (accumulator, clusteringCoefficient) -> accumulator.addClusteringCoefficient(clusteringCoefficient))
              .getAvgClusteringCoefficientAsAccumulator();
        }).reduce(new ClusteringCoefficientAccumulator(), (accumulator, clusteringCoefficient) ->
                accumulator.addClusteringCoefficient(clusteringCoefficient))
          .getAvgClusteringCoefficient();
    }

    /**
     * Computes the general mixed hypergraph density that takes into account directed and undirected hyperedges.
     */
    public double computeDensity() {
        long n = graph.getNumberOfVertices();
        long m = graph.getNumberOfEdges();

        long accumU = 0;
        long accumD = 0;

        for (IntCursor edgeCursor : IntCursor.fromFastUtil(graph.getEdges())) {
            if (graph.isUndirectedHyperEdge(edgeCursor.value)) {
                int k = graph.getEdgeDegree(edgeCursor.value);
                accumU += k;
            } else if (graph.isDirectedHyperEdge(edgeCursor.value)) {
                int k1 = graph.getDirectedHyperEdgeTail(edgeCursor.value).size();
                int k2 = graph.getDirectedHyperEdgeHead(edgeCursor.value).size();
                accumD += k1 + k2;
            }
        }

        // Denominator multiplied by 2 to account for all directed and undirected hyperedges,
        // assuming a combination of two simples hypergraphs, one directed and one undirected.
        return (double) (2 * accumU + accumD) / (2 * (n + m) * (n + m - 1));
    }

    public void exportStats(String workdir) throws IOException {
        exportStats(workdir, "stats");
    }

    public void exportStats(String workdir, String prefix) throws IOException {
        String now = isoDateFormat.format(new Date());

        Path path = Paths.get(workdir, String.format("%s-%s.csv", prefix, now));
        try (BufferedWriter writer = Files.newBufferedWriter(path);
                CSVPrinter csvPrinter = new CSVPrinter(writer, CSVFormat.DEFAULT.withHeader("Statistic", "Value"))) {

            logger.info("Computing general statistics");
            csvPrinter.printRecord("Vertices", graph.getNumberOfVertices());
            csvPrinter.printRecord("Directed Hyperedges", graph.getNumberOfDirectedHyperEdges());
            csvPrinter.printRecord("Undirected Hyperedges", graph.getNumberOfUndirectedEdges());
            csvPrinter.printRecord("Total Hyperedges", graph.getNumberOfHyperEdges());
            csvPrinter.printRecord("Num Sources", graph.getSources().size());
            csvPrinter.printRecord("Num Sinks", graph.getSinks().size());
            csvPrinter.flush();

            logger.info("Computing general hypergraph density");
            csvPrinter.printRecord("Density", computeDensity());
            csvPrinter.flush();

            logger.info("Computing average degree");
            csvPrinter.printRecord("Avg. Degree", graph.getAverageDegree());
            csvPrinter.flush();

            logger.info("Computing minimum degree of incoming edges");
            csvPrinter.printRecord("Min InEdge Degree", graph.getMinInEdgeDegrees());
            csvPrinter.flush();

            logger.info("Computing maximum degree of incoming edges");
            csvPrinter.printRecord("Max InEdge Degree", graph.getMaxInEdgeDegrees());
            csvPrinter.flush();

            logger.info("Computing minimum degree of incoming vertices");
            csvPrinter.printRecord("Min InVertex Degree", graph.getMinInVertexDegrees());
            csvPrinter.flush();

            logger.info("Computing maximum degree of incoming vertices");
            csvPrinter.printRecord("Max InVertex Degree", graph.getMaxInVertexDegrees());
            csvPrinter.flush();

            logger.info("Computing minimum degree of outgoing edges");
            csvPrinter.printRecord("Min OutEdge Degree", graph.getMinOutEdgeDegrees());
            csvPrinter.flush();

            logger.info("Computing maximum degree of outgoing edges");
            csvPrinter.printRecord("Max OutEdge Degree", graph.getMaxOutEdgeDegrees());
            csvPrinter.flush();

            logger.info("Computing minimum degree of outgoing vertices");
            csvPrinter.printRecord("Min OutVertex Degree", graph.getMinOutVertexDegrees());
            csvPrinter.flush();

            logger.info("Computing minimum degree of outgoing vertices");
            csvPrinter.printRecord("Max OutVertex Degree", graph.getMaxOutVertexDegrees());
            csvPrinter.flush();

            logger.info("Estimating average two-node clustering coefficient using node sampling");
            csvPrinter.printRecord("Avg. Clustering Coefficient", estimateClusteringCoefficient(5000, 100000));
            csvPrinter.flush();

            logger.info("Estimating average path length and diameter using random walks");
            int [] shortestDistances = estimateShortestDistances(30, 1000, 1000);
            csvPrinter.printRecord("Diameter", Arrays.stream(shortestDistances).max().getAsInt());
            csvPrinter.printRecord("Avg. Path Length",
                (float) Arrays.stream(shortestDistances).sum() / shortestDistances.length);
            csvPrinter.flush();
        }
    }

    public void exportSpaceUsage(String workdir) throws IOException {
        String now = isoDateFormat.format(new Date());

        Path path = Paths.get(workdir, String.format("space-usage-%s.csv", now));
        try (BufferedWriter writer = Files.newBufferedWriter(path);
                CSVPrinter csvPrinter = new CSVPrinter(writer, CSVFormat.DEFAULT.withHeader("Statistic", "Value"))) {

            logger.info("Computing disk space and memory usage");
            csvPrinter.printRecord(
                "Disk (Bytes)", FileUtils.sizeOfDirectoryAsBigInteger(this.directory));
            csvPrinter.printRecord(
                "Memory (Bytes)", Runtime.getRuntime().totalMemory() - Runtime.getRuntime().freeMemory());
        }
    }

    public void exportRandomHypergraphStats(String workdir) throws IOException {
        exportRandomHypergraphStats(workdir, true);
    }

    public void exportRandomHypergraphStats(String workdir, boolean reload) throws IOException {
        /*logger.info("Getting number of nodes from original hypergraph and unloading it");
        int numNodes = graph.getNumberOfVertices();
        unload();

        InMemoryGrph randomGraph = new InMemoryGrph();

        logger.info("Adding {} nodes", numNodes);
        for (int i=0; i < numNodes; i++) {
            randomGraph.addVertex();
        }

        logger.info("Wiring ");

        logger.info("Reloading hypergraph");
        load();*/
        throw new NotYetImplementedException("Requires a model for generating a random hypergraph");
    }

    public void export(String feature, String workdir) throws IOException {
        if (!Files.exists(Paths.get(workdir))) {
            logger.info("Creating working directory: {}", workdir);
            Files.createDirectories(Paths.get(workdir));
        }

        if (feature.equals("export-node-weights")) {
            exportNodeWeights(workdir);
        } else if (feature.equals("export-edge-weights")) {
            exportEdgeWeights(workdir);
        } else if (feature.equals("export-node-degree")) {
            exportNodeDegree(workdir);
        } else if (feature.equals("export-edge-cardinality")) {
            exportEdgeCardinality(workdir);
        } else if (feature.equals("export-stats")) {
            exportStats(workdir);
        } else if (feature.equals("export-space-usage")) {
            exportSpaceUsage(workdir);
        } else if (feature.equals("export-random-hypergraph-stats")) {
            exportRandomHypergraphStats(workdir);
        } else if (feature.equals("export-wordnet-noun-syns-distr")) {
            // TODO This should move into another place (maybe Engine), since it doesn't depend on the index.
            exportWordNetNounSynsDistr(workdir);
        } else {
            logger.error("Invalid feature {}", feature);
        }
    }

    @Override
    public void inspect(String feature, String workdir) {
        boolean valid = true;
        Trace trace = null;
        if (feature.equals("summary")) {
            trace = getSummary();
        } else if (feature.equals("synonym-summary")) {
            trace = getSummaryByUndirectedEdgeType(TermNode.class, SynonymEdge.class);
        } else if (feature.equals("context-summary")) {
            trace = getSummaryByUndirectedEdgeType(TermNode.class, ContextEdge.class);
        } else if (feature.equals("tfbin-summary")) {
            trace = getSummaryByUndirectedEdgeType(TermNode.class, TFBinEdge.class);
        } else if (feature.equals("list-nodes")) {
            trace = getNodeList();
        } else if (feature.equals("list-hyperedges")) {
            trace = getHyperedgeList();
        } else if (feature.startsWith("export-")) {
            try {
                export(feature, workdir);
            } catch (IOException e) {
                logger.error(e.getMessage(), e);
            }
            return;
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
        ALL_PATHS,
    }

    private enum EntityIndexingStrategy {
        DOCUMENT_COOCCURRENCE,
        GROUP_BY_SUBJECT,
    }

    public enum RankingFunction {
        ENTITY_WEIGHT,
        JACCARD_SCORE,
        RANDOM_WALK_SCORE,
        HYPERRANK,
    }

    public enum Feature {
        SENTENCES,
        SYNONYMS,
        CONTEXT,
        TF_BINS,
        WEIGHT,
        PRUNE,
        SKIP_RELATED_TO,
        RELATED_TO_BY_DOC,
        RELATED_TO_BY_SUBJ,
    }
}