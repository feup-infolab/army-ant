package armyant.hgoe.indisk;

import armyant.hgoe.HypergraphOfEntity;
import armyant.hgoe.indisk.edges.ContainedInEdge;
import armyant.hgoe.indisk.edges.DocumentEdge;
import armyant.hgoe.indisk.edges.Edge;
import armyant.hgoe.indisk.edges.RelatedToEdge;
import armyant.hgoe.indisk.nodes.DocumentNode;
import armyant.hgoe.indisk.nodes.EntityNode;
import armyant.hgoe.indisk.nodes.Node;
import armyant.hgoe.indisk.nodes.TermNode;
import armyant.hgoe.indisk.traversals.AllPaths;
import armyant.hgoe.structures.Document;
import armyant.hgoe.structures.Result;
import armyant.hgoe.structures.ResultSet;
import org.apache.commons.collections4.map.LRUMap;
import org.hypergraphdb.*;
import org.hypergraphdb.algorithms.HGALGenerator;
import org.hypergraphdb.algorithms.HGDepthFirstTraversal;
import org.hypergraphdb.algorithms.SimpleALGenerator;
import org.hypergraphdb.handle.SequentialUUIDHandleFactory;
import org.hypergraphdb.indexing.ByPartIndexer;
import org.hypergraphdb.storage.bje.BJEConfig;
import org.hypergraphdb.util.Pair;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.util.*;
import java.util.stream.Collectors;

import static org.hypergraphdb.HGQuery.hg.*;

/**
 * Created by jldevezas on 2017-10-23.
 */
public class HypergraphOfEntityInDisk extends HypergraphOfEntity {
    private static final Logger logger = LoggerFactory.getLogger(HypergraphOfEntityInDisk.class);
    private static final Integer SEARCH_MAX_DISTANCE = 2;

    private HGConfiguration config;
    private HyperGraph graph;

    private LRUMap<Node, HGHandle> nodeCache;

    private long counter;
    private long totalTime;
    private float avgTimePerDocument;

    public HypergraphOfEntityInDisk(String path) {
        this(path, false);
    }

    public HypergraphOfEntityInDisk(String path, boolean bulkLoad) {
        super();

        logger.info("Using in-disk version of Hypergraph of Entity");

        nodeCache = new LRUMap<>(1000000);

        avgTimePerDocument = 0f;
        counter = 0;

        config = new HGConfiguration();
        config.setTransactional(false);

        if (bulkLoad) {
            config.setSkipMaintenance(true);

            SequentialUUIDHandleFactory handleFactory = new SequentialUUIDHandleFactory(System.currentTimeMillis(), 0);
            config.setHandleFactory(handleFactory);
        }

        BJEConfig bjeConfig = (BJEConfig) config.getStoreImplementation().getConfiguration();
        bjeConfig.getEnvironmentConfig().setCacheSize(1024 * 1024 * 1024); // 1 GB

        this.graph = HGEnvironment.get(path, config);

        HGHandle nodeType = graph.getTypeSystem().getTypeHandle(Node.class);
        graph.getIndexManager().register(new ByPartIndexer(nodeType, "name"));

        // Covered by nodeType index?
        /*HGHandle termNodeType = graph.getTypeSystem().getTypeHandle(TermNode.class);
        graph.getIndexManager().register(new ByPartIndexer(termNodeType, "name"));

        HGHandle entityNodeType = graph.getTypeSystem().getTypeHandle(EntityNode.class);
        graph.getIndexManager().register(new ByPartIndexer(entityNodeType, "name"));*/
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

        HGALGenerator generator = new SimpleALGenerator(graph);
        Set<HGHandle> reachedSeedNodes = new HashSet<>();

        HGDepthFirstTraversal traversal = new HGDepthFirstTraversal(entity, generator);
        while (traversal.hasNext()) {
            Pair<HGHandle, HGHandle> current = traversal.next();
            HGHandle nodeHandle = current.getSecond();
            if (seedNodes.contains(nodeHandle)) reachedSeedNodes.add(nodeHandle);

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

    private double confidenceWeight(HGHandle seedNode, Map<String, HGHandle> queryTermNodeHandles) {
        if (seedNode == null) return 0;

        if (graph.get(seedNode) instanceof TermNode) return 1;

        Set<HGHandle> neighbors = getNeighbors(seedNode, ContainedInEdge.class);

        Set<HGHandle> linkedQueryTermNodes = new HashSet<>(neighbors);
        linkedQueryTermNodes.retainAll(queryTermNodeHandles.values());

        return (double) linkedQueryTermNodes.size() / neighbors.size();
    }

    public Map<HGHandle, Double> seedNodeConfidenceWeights(Set<HGHandle> seedNodes, Map<String, HGHandle> queryTermNodeHandles) {
        Map<HGHandle, Double> weights = new HashMap<>();

        for (HGHandle seedNode : seedNodes) {
            weights.put(seedNode, confidenceWeight(seedNode, queryTermNodeHandles));
        }

        return weights;
    }

    public double entityWeight(HGHandle entityHandle, Map<HGHandle, Double> seedNodeWeights) {
        double score = 0d;

        // Get all paths between the entity and a seed node (within a maximum distance; null by default).
        for (HGHandle seedNodeHandle : seedNodeWeights.keySet()) {
            logger.debug("Calculating score based on seed {}", graph.get(seedNodeHandle).toString());

            double seedScore = 0d;

            AllPaths allPaths = new AllPaths(graph, entityHandle, seedNodeHandle, SEARCH_MAX_DISTANCE);
            allPaths.traverse();
            List<List<HGHandle>> paths = allPaths.getPaths();

            for (List<HGHandle> path : paths) {
                seedScore += seedNodeWeights.get(seedNodeHandle) * 1d / path.size();
            }
            seedScore = paths.isEmpty() ? 0 : seedScore / paths.size();

            score += seedScore;
        }

        score = seedNodeWeights.isEmpty() ? 0 : score / seedNodeWeights.size();

        return score * coverage(entityHandle, seedNodeWeights.keySet());
    }

    public ResultSet search(String query) throws IOException {
        ResultSet resultSet = new ResultSet();

        List<String> tokens = analyze(query);
        Map<String, HGHandle> queryTermNodeHandles = getQueryTermNodes(tokens);

        Set<HGHandle> seedNodeHandles = getSeedNodes(queryTermNodeHandles);
        System.out.println("Seed Nodes: " + seedNodeHandles.stream().map(graph::get).collect(Collectors.toList()));

        Map<HGHandle, Double> seedNodeWeights = seedNodeConfidenceWeights(seedNodeHandles, queryTermNodeHandles);
        System.out.println("Seed Node Confidence Weights: " + seedNodeWeights);

        HGSearchResult<HGHandle> rs = null;
        try {
            rs = graph.find(type(EntityNode.class));
            while (rs.hasNext()) {
                HGHandle entityNodeHandle = rs.next();
                Node entityNode = graph.get(entityNodeHandle);
                logger.debug("Ranking {}", entityNode);
                double score = entityWeight(entityNodeHandle, seedNodeWeights);
                if (score > 0) resultSet.addResult(new Result(graph.get(entityNodeHandle), score));
                //System.out.println(((Node) graph.get(entityNodeHandle)).getName() + ": " + score);
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
    }
}