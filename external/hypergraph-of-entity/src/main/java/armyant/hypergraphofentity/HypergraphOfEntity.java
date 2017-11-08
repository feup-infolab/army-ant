package armyant.hypergraphofentity;

import armyant.hypergraphofentity.edges.ContainedInEdge;
import armyant.hypergraphofentity.edges.DocumentEdge;
import armyant.hypergraphofentity.edges.Edge;
import armyant.hypergraphofentity.edges.RelatedToEdge;
import armyant.hypergraphofentity.nodes.DocumentNode;
import armyant.hypergraphofentity.nodes.EntityNode;
import armyant.hypergraphofentity.nodes.Node;
import armyant.hypergraphofentity.nodes.TermNode;
import armyant.hypergraphofentity.traversals.AllPaths;
import com.optimaize.langdetect.LanguageDetector;
import com.optimaize.langdetect.LanguageDetectorBuilder;
import com.optimaize.langdetect.i18n.LdLocale;
import com.optimaize.langdetect.ngram.NgramExtractors;
import com.optimaize.langdetect.profiles.LanguageProfile;
import com.optimaize.langdetect.profiles.LanguageProfileReader;
import org.apache.commons.collections4.map.LRUMap;
import org.apache.commons.io.IOUtils;
import org.apache.lucene.analysis.CharArraySet;
import org.apache.lucene.analysis.LowerCaseFilter;
import org.apache.lucene.analysis.StopFilter;
import org.apache.lucene.analysis.TokenStream;
import org.apache.lucene.analysis.standard.StandardFilter;
import org.apache.lucene.analysis.standard.StandardTokenizer;
import org.apache.lucene.analysis.tokenattributes.CharTermAttribute;
import org.apache.lucene.util.AttributeFactory;
import org.hypergraphdb.*;
import org.hypergraphdb.algorithms.*;
import org.hypergraphdb.handle.SequentialUUIDHandleFactory;
import org.hypergraphdb.indexing.ByPartIndexer;
import org.hypergraphdb.storage.bje.BJEConfig;
import org.hypergraphdb.util.Pair;
import org.joda.time.Duration;
import org.joda.time.format.PeriodFormatter;
import org.joda.time.format.PeriodFormatterBuilder;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.io.InputStream;
import java.io.StringReader;
import java.io.StringWriter;
import java.util.*;
import java.util.stream.Collectors;

import static org.hypergraphdb.HGQuery.hg.*;

/**
 * Created by jldevezas on 2017-10-23.
 */
public class HypergraphOfEntity {
    private static final Logger logger = LoggerFactory.getLogger(HypergraphOfEntity.class);
    private static final int DEFAULT_MAX_DISTANCE = 3;

    private HGConfiguration config;
    private HyperGraph graph;

    private LRUMap<Node, HGHandle> nodeCache;
    private LanguageDetector languageDetector;

    private long counter;
    private long totalTime;
    private float avgTimePerDocument;

    public HypergraphOfEntity(String path) {
        nodeCache = new LRUMap<>(1000000);

        avgTimePerDocument = 0f;
        counter = 0;

        config = new HGConfiguration();
        config.setSkipMaintenance(true);
        config.setTransactional(false);

        SequentialUUIDHandleFactory handleFactory = new SequentialUUIDHandleFactory(System.currentTimeMillis(), 0);
        config.setHandleFactory(handleFactory);

        BJEConfig bjeConfig = (BJEConfig) config.getStoreImplementation().getConfiguration();
        bjeConfig.getEnvironmentConfig().setCacheSize(1024 * 1024 * 1024); // 1 GB

        this.graph = HGEnvironment.get(path, config);

        HGHandle nodeType = graph.getTypeSystem().getTypeHandle(Node.class);
        graph.getIndexManager().register(new ByPartIndexer(nodeType, "name"));

        HGHandle termNodeType = graph.getTypeSystem().getTypeHandle(TermNode.class);
        graph.getIndexManager().register(new ByPartIndexer(termNodeType, "name"));

        HGHandle entityNodeType = graph.getTypeSystem().getTypeHandle(EntityNode.class);
        graph.getIndexManager().register(new ByPartIndexer(entityNodeType, "name"));

        try {
            List<LanguageProfile> languageProfiles = new LanguageProfileReader().readAllBuiltIn();
            languageDetector = LanguageDetectorBuilder.create(NgramExtractors.standard())
                    .withProfiles(languageProfiles)
                    .build();
        } catch (IOException e) {
            logger.error(e.getMessage(), e);
        }
    }

    public String formatMillis(float millis) {
        if (millis >= 1000) return formatMillis((long) millis);
        return String.format("%.2fms", millis);
    }

    public String formatMillis(long millis) {
        Duration duration = new Duration(millis); // in milliseconds
        PeriodFormatter formatter = new PeriodFormatterBuilder()
                .appendDays()
                .appendSuffix("d")
                .appendHours()
                .appendSuffix("h")
                .appendMinutes()
                .appendSuffix("m")
                .appendSeconds()
                .appendSuffix("s")
                .appendMillis()
                .appendSuffix("ms")
                .toFormatter();
        return formatter.print(duration.toPeriod());
    }

    public void close() {
        graph.close();
    }

    public Map<? extends Node, HGHandle> multipleImport(final List<? extends Node> atoms) {
        if (atoms.isEmpty()) return new HashMap<>();

        final Map<Node, HGHandle> handleMap = new HashMap<>(atoms.size());
        final Node first = atoms.iterator().next();
        HGHandle firstH = assertAtom(graph, first);
        handleMap.put(first, firstH);
        final HGHandle typeHandle = graph.getType(firstH);

        for (Node node : atoms.subList(1, atoms.size())) {
            HGHandle handle = handleMap.get(node);
            if (handle == null) {
                handle = nodeCache.get(node);
                if (handle == null) {
                    handle = assertAtom(graph, node, typeHandle);
                    nodeCache.put(node, handle);
                }
                handleMap.put(node, handle);
            }
        }

        return handleMap;
    }

    // I could only use this with the guarantee that all atoms are distinct!
    public Map<? extends Node, HGHandle> bulkImport(final Collection<? extends Node> atoms) {
        if (atoms.isEmpty()) return new HashMap<>();

        final Map<Node, HGHandle> handleMap = new HashMap<>(atoms.size());
        final Node first = atoms.iterator().next();
        HGHandle firstH = graph.add(first);
        handleMap.put(first, firstH);
        final HGHandle typeHandle = graph.getType(firstH);

        if (config.isTransactional())
            graph.getTransactionManager().ensureTransaction(() -> assertAtomLight(atoms, typeHandle, handleMap));
        else
            assertAtomLight(atoms, typeHandle, handleMap);

        return handleMap;
    }

    public boolean assertAtomLight(Collection<? extends Node> atoms, HGHandle typeHandle, Map<Node, HGHandle> handleMap) {
        for (Node atom : atoms) {
            HGHandle handle = handleMap.get(atom);
            if (handle == null) {
                handle = nodeCache.get(atom);
                if (handle == null) {
                    handle = graph.add(atom, typeHandle);
                    nodeCache.put(atom, handle);
                }
                handleMap.put(atom, handle);
            }
        }
        return true;
    }


    private CharArraySet getStopwords(String language) {
        StringWriter writer = new StringWriter();

        logger.debug("Fetching stopwords for {} language", language);

        String defaultFilename = "/stopwords/en.stopwords";
        String filename = String.format("/stopwords/%s.stopwords", language);

        try {
            InputStream inputStream = getClass().getResourceAsStream(filename);
            if (inputStream == null) {
                logger.warn("Could not load '{}' stopwords, using 'en' as default", language);
                inputStream = getClass().getResourceAsStream(defaultFilename);
            }
            IOUtils.copy(inputStream, writer, "UTF-8");
            return new CharArraySet(Arrays.asList(writer.toString().split("\n")), true);
        } catch (IOException e) {
            logger.warn("Could not load 'en' stopwords, ignoring stopwords");
            return CharArraySet.EMPTY_SET;
        }
    }

    private List<String> analyze(String text) throws IOException {
        AttributeFactory factory = AttributeFactory.DEFAULT_ATTRIBUTE_FACTORY;

        StandardTokenizer tokenizer = new StandardTokenizer(factory);
        tokenizer.setReader(new StringReader(text));

        String language = languageDetector.detect(text).or(LdLocale.fromString("en")).getLanguage();

        TokenStream filter = new StandardFilter(tokenizer);
        filter = new LowerCaseFilter(filter);
        filter = new StopFilter(filter, getStopwords(language));
        filter.reset();

        List<String> tokens = new ArrayList<>();
        CharTermAttribute attr = tokenizer.addAttribute(CharTermAttribute.class);
        while (filter.incrementToken()) {
            tokens.add(attr.toString());
        }

        return tokens;
    }


    private Set<HGHandle> indexDocument(Document document, Set<HGHandle> entityHandles) throws IOException {
        List<String> tokens = analyze(document.getText());
        if (tokens.isEmpty()) return new HashSet<>();

        Set<HGHandle> nodeHandles = new HashSet<>(entityHandles);

        DocumentNode documentNode = new DocumentNode(document.getDocID());
        HGHandle documentNodeHandle = assertAtom(graph, documentNode);

        List<TermNode> termNodes = tokens.stream().map(TermNode::new).collect(Collectors.toList());

        Map<? extends Node, HGHandle> termHandleMap = multipleImport(termNodes);
        nodeHandles.addAll(termHandleMap.values());

        DocumentEdge link = new DocumentEdge(
                document.getDocID(),
                new HGHandle[]{documentNodeHandle},
                nodeHandles.toArray(new HGHandle[nodeHandles.size()]));
        graph.add(link);

        return new HashSet<>(termHandleMap.values());
    }

    private Set<HGHandle> indexEntities(Document document) {
        Map<EntityNode, Set<EntityNode>> edges = document.getTriples().stream()
                .collect(Collectors.groupingBy(
                        t -> new EntityNode(t.getSubject()),
                        Collectors.mapping(t -> new EntityNode(t.getObject()), Collectors.toSet())));

        List<EntityNode> entityNodes = new ArrayList<>(edges.keySet());
        entityNodes.addAll(edges.values().stream().flatMap(Set::stream).collect(Collectors.toSet()));
        Map<? extends Node, HGHandle> entityHandleMap = multipleImport(entityNodes);

        for (Map.Entry<EntityNode, Set<EntityNode>> entry : edges.entrySet()) {
            RelatedToEdge link = new RelatedToEdge(
                    new HGHandle[]{entityHandleMap.get(entry.getKey())},
                    entry.getValue().stream().map(entityHandleMap::get).toArray(HGHandle[]::new));
            graph.add(link);
        }

        return new HashSet<>(entityHandleMap.values());
    }

    private void linkTextAndKnowledge(Set<HGHandle> termHandles, Set<HGHandle> entityHandles) {
        for (HGHandle entityHandle : entityHandles) {
            Set<HGHandle> handles = new HashSet<>();

            EntityNode entity = graph.get(entityHandle);

            for (HGHandle termHandle : termHandles) {
                TermNode term = graph.get(termHandle);
                if (entity.getName().toLowerCase().matches(".*\\b" + term.getName().toLowerCase() + "\\b.*")) {
                    handles.add(termHandle);
                }
            }

            if (handles.isEmpty()) continue;

            ContainedInEdge link = new ContainedInEdge(
                    handles.toArray(new HGHandle[handles.size()]),
                    new HGHandle[]{entityHandle});
            graph.add(link);
        }
    }

    public void index(Document document) throws IOException {
        long startTime = System.currentTimeMillis();

        Set<HGHandle> entityHandles = indexEntities(document);
        Set<HGHandle> termHandles = indexDocument(document, entityHandles);
        linkTextAndKnowledge(termHandles, entityHandles);

        long time = System.currentTimeMillis() - startTime;
        totalTime += time;

        counter++;
        avgTimePerDocument = counter > 1 ? (avgTimePerDocument * (counter - 1) + time) / counter : time;

        if (counter % 10 == 0) {
            logger.info(
                    "{} indexed documents in {} (avg./doc: {})",
                    counter, formatMillis(totalTime), formatMillis(avgTimePerDocument));
        }
    }


    private Map<String, HGHandle> getQueryTermNodes(List<String> terms) {
        Map<String, HGHandle> termNodeMap = new HashMap<>();

        for (String term : terms) {
            HGHandle termNode = graph.findOne(and(type(TermNode.class), eq("name", term)));
            if (termNode != null) termNodeMap.put(term, termNode);
        }

        return termNodeMap;
    }

    private Set<HGHandle> getSeedNodes(Map<String, HGHandle> queryTermNodes) {
        Set<HGHandle> seedNodes = new HashSet<>();

        for (HGHandle queryTermNode : queryTermNodes.values()) {
            Set<HGHandle> localSeedNodes = new HashSet<>();

            HGSearchResult<HGHandle> rs = graph.find(and(type(ContainedInEdge.class), link(queryTermNode)));

            try {
                while (rs.hasNext()) {
                    HGHandle current = rs.next();
                    ContainedInEdge link = graph.get(current);
                    for (HGHandle handle : link.getTail()) {
                        Node node = graph.get(handle);
                        if (node instanceof EntityNode) {
                            localSeedNodes.add(handle);
                        }
                    }
                }

                if (localSeedNodes.isEmpty()) {
                    localSeedNodes.add(queryTermNode);
                }

                seedNodes.addAll(localSeedNodes);
            } catch (Throwable t) {
                graph.getTransactionManager().abort();
            } finally {
                rs.close();
            }
        }

        return seedNodes;
    }

    private double coverage(HGHandle entity, Set<HGHandle> seedNodes) {
        if (seedNodes.isEmpty()) return 0d;

        HGALGenerator generator = new SimpleALGenerator(this.graph);
        Set<HGHandle> reachedSeedNodes = new HashSet<>();

        for (HGHandle seedNode : seedNodes) {
            Double distance = GraphClassics.dijkstra(entity, seedNode, generator);
            if (distance != null) {
                reachedSeedNodes.add(seedNode);
            }
        }

        return (double) reachedSeedNodes.size() / seedNodes.size();
    }

    private List<HGHandle> collectNodesFromEdge(Edge edge) {
        List<HGHandle> nodes = new ArrayList<>();

        for (int i = 0; i < edge.getArity(); i++) {
            HGHandle handle = edge.getTargetAt(i);
            Object atom = graph.get(handle);
            if (atom instanceof Node) {
                nodes.add(handle);
            } else if (atom instanceof Edge) {
                nodes.addAll(collectNodesFromEdge((Edge) atom));
            }
        }

        return nodes;
    }

    private Set<HGHandle> getNeighbors(HGHandle sourceNodeHandle, Class edgeType) {
        Set<HGHandle> nodes = new HashSet<>();

        HGRandomAccessResult<HGHandle> incidentEdges = graph.getIncidenceSet(sourceNodeHandle).getSearchResult();
        while (incidentEdges.hasNext()) {
            HGHandle edgeHandle = incidentEdges.next();
            Edge edge = graph.get(edgeHandle);
            if (edgeType.isInstance(edge)) {
                nodes.addAll(collectNodesFromEdge(edge));
            }
        }

        nodes.remove(sourceNodeHandle);

        return nodes;
    }

    private double confidenceWeight(HGHandle seedNode, Set<HGHandle> queryTermNodes) {
        if (seedNode == null) return 0;

        if (graph.get(seedNode) instanceof TermNode) return 1;

        Set<HGHandle> neighbors = getNeighbors(seedNode, ContainedInEdge.class);
        //System.out.println("Neighbors: " + neighbors.stream().map(graph::get).collect(Collectors.toList()));

        /*for (HGHandle incidentNode : neighbors) {
            Object atom = graph.get(incidentNode);
            if (atom instanceof TermNode) {
                System.out.println(atom);
            }
        }*/

        double degree = neighbors.size();

        Set<HGHandle> linkedQueryTermNodes = new HashSet<>(neighbors);
        linkedQueryTermNodes.retainAll(queryTermNodes);

        /*System.out.println(linkedQueryTermNodes);
        System.out.println(neighbors);*/

        return (double) linkedQueryTermNodes.size() / neighbors.size();
    }

    public Map<HGHandle, Double> seedNodeConfidenceWeights(Set<HGHandle> seedNodes, Set<HGHandle> queryTermNodes) {
        Map<HGHandle, Double> weights = new HashMap<>();

        for (HGHandle seedNode : seedNodes) {
            weights.put(seedNode, confidenceWeight(seedNode, queryTermNodes));
        }

        return weights;
    }

    public List<List<HGHandle>> getAllPaths(HGHandle source, HGHandle target) {
        return getAllPaths(source, target, DEFAULT_MAX_DISTANCE);
    }

    public List<List<HGHandle>> getAllPaths(HGHandle source, HGHandle target, int maxDistance) {
        Node sourceNode = graph.get(source);
        Node targetNode = graph.get(target);
        System.out.println("Source: " + sourceNode.toString() + " Target: " + targetNode.toString());

        AllPaths allPaths = new AllPaths(graph, source, target);
        allPaths.traverse();
        return allPaths.getPaths();
    }

    public double entityWeight(HGHandle entity, Set<HGHandle> seedNodes) {
        //double score = coverage(entity, seedNodes) * confidenceWeight(entity, seedNodes) * 1d/seedNodes.size() *

        // get all paths between the entity and a seed node (within a maximum distance)
        // constrained (by max distance) depth first search?
        HGHandle seedNode = seedNodes.iterator().next();
        List<List<HGHandle>> paths = getAllPaths(entity, seedNode);
        for (List<HGHandle> path : paths) {
            path.forEach(h -> System.out.println(graph.get(h).toString()));
        }

        return 0d;
    }

    public ResultSet search(String query) throws IOException {
        ResultSet resultSet = new ResultSet();

        List<String> tokens = analyze(query);

        Map<String, HGHandle> queryTermNodes = getQueryTermNodes(tokens);

        Set<HGHandle> seedNodes = getSeedNodes(queryTermNodes);
        System.out.println("Seed Nodes: " + seedNodes.stream().map(graph::get).collect(Collectors.toList()));

        Map<HGHandle, Double> seedNodeWeights = seedNodeConfidenceWeights(seedNodes, new HashSet<>(queryTermNodes.values()));
        System.out.println("Seed Node Confidence Weights: " + seedNodeWeights);

        HGSearchResult<HGHandle> rs = null;
        try {
            rs = graph.find(type(EntityNode.class));
            while (rs.hasNext()) {
                HGHandle entityNodeHandle = rs.next();
                System.out.println(((Node) graph.get(entityNodeHandle)).getName() + ": " + entityWeight(entityNodeHandle, seedNodes));
            }
        } finally {
            rs.close();
        }

        return resultSet;
    }


    public void printStatistics() {
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
            Object atom = graph.get(current.getSecond());
            System.out.println("Visiting atom " + atom + " pointed to by " + l);
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
    }
}
