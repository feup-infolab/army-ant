package armyant.hypergraphofentity;

import armyant.hypergraphofentity.edges.ContainedInEdge;
import armyant.hypergraphofentity.edges.DocumentEdge;
import armyant.hypergraphofentity.edges.Edge;
import armyant.hypergraphofentity.edges.RelatedToEdge;
import armyant.hypergraphofentity.nodes.DocumentNode;
import armyant.hypergraphofentity.nodes.EntityNode;
import armyant.hypergraphofentity.nodes.Node;
import armyant.hypergraphofentity.nodes.TermNode;
import org.apache.commons.collections4.map.LRUMap;
import org.apache.lucene.analysis.standard.StandardTokenizer;
import org.apache.lucene.analysis.tokenattributes.CharTermAttribute;
import org.apache.lucene.util.AttributeFactory;
import org.hypergraphdb.*;
import org.hypergraphdb.algorithms.GraphClassics;
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
import java.io.StringReader;
import java.util.*;
import java.util.stream.Collectors;

import static org.hypergraphdb.HGQuery.hg.*;

/**
 * Created by jldevezas on 2017-10-23.
 */
public class HypergraphOfEntity {
    public static final int TRANSACTION_SIZE = 100;
    private static final Logger logger = LoggerFactory.getLogger(HypergraphOfEntity.class);

    private String path;
    private HGConfiguration config;
    private HyperGraph graph;
    private long indexedCounter;
    private Long batchStartTime;
    private boolean batch;

    private LRUMap<Node, HGHandle> nodeCache;
    //private LRUMap<Edge, HGHandle> edgeCache;

    public HypergraphOfEntity(String path) {
        this(path, false);
    }

    public HypergraphOfEntity(String path, boolean batch) {
        this.path = path;
        this.batch = batch;
        this.nodeCache = new LRUMap<>(100000);
        //this.edgeCache = new LRUMap<>(10000);

        indexedCounter = 0;

        config = new HGConfiguration();
        config.setTransactional(true);
        //config.setSkipOpenedEvent(true);
        config.setUseSystemAtomAttributes(false);
        //config.setSkipMaintenance(true);
        //config.setMaxCachedIncidenceSetSize(10000000);

        SequentialUUIDHandleFactory handleFactory = new SequentialUUIDHandleFactory(System.currentTimeMillis(), 0);
        config.setHandleFactory(handleFactory);

        BJEConfig bjeConfig = (BJEConfig) config.getStoreImplementation().getConfiguration();
        bjeConfig.getEnvironmentConfig().setCacheSize(1024 * 1024 * 1024);

        this.graph = HGEnvironment.get(this.path, config);

        HGHandle nodeType = graph.getTypeSystem().getTypeHandle(Node.class);
        graph.getIndexManager().register(new ByPartIndexer(nodeType, "name"));

        HGHandle termNodeType = graph.getTypeSystem().getTypeHandle(TermNode.class);
        graph.getIndexManager().register(new ByPartIndexer(termNodeType, "name"));

        HGHandle entityNodeType = graph.getTypeSystem().getTypeHandle(EntityNode.class);
        graph.getIndexManager().register(new ByPartIndexer(entityNodeType, "name"));

        if (batch) {
            logger.info("Using batch commit with transaction size = {}", TRANSACTION_SIZE);
            this.graph.getTransactionManager().beginTransaction();
        }
    }

    public void close() {
        if (batch) {
            this.graph.getTransactionManager().commit();
        }
        this.graph.close();
    }


    private List<String> tokenize(String text) throws IOException {
        AttributeFactory factory = AttributeFactory.DEFAULT_ATTRIBUTE_FACTORY;

        StandardTokenizer tokenizer = new StandardTokenizer(factory);
        tokenizer.setReader(new StringReader(text.toLowerCase()));
        tokenizer.reset();

        List<String> tokens = new ArrayList<>();
        CharTermAttribute attr = tokenizer.addAttribute(CharTermAttribute.class);
        while (tokenizer.incrementToken()) {
            tokens.add(attr.toString());
        }

        return tokens;
    }


    private Set<HGHandle> indexDocument(Document document, Set<HGHandle> entityHandles) throws IOException {
        logger.debug("Entering indexDocument() for document {}", document.getDocID());

        List<String> tokens = tokenize(document.getText());

        Set<HGHandle> nodeHandles = new HashSet<>();
        Set<HGHandle> termHandles = new HashSet<>();

        if (tokens.isEmpty()) return termHandles;

        DocumentNode documentNode = new DocumentNode(document.getDocID());
        nodeHandles.add(assertAtom(graph, documentNode));

        nodeHandles.addAll(entityHandles);

        Node firstNode = new TermNode(tokens.get(0));
        HGHandle termTypeHandle = graph.getType(assertAtom(graph, firstNode));
        for (String term : tokens.subList(1, tokens.size())) {
            Node node = new TermNode(term);

            HGHandle handle = nodeCache.get(node);
            if (handle == null) {
                handle = assertAtom(graph, node, termTypeHandle);
                nodeCache.put(node, handle);
            }

            nodeHandles.add(handle);
            termHandles.add(handle);
        }

        DocumentEdge link = new DocumentEdge(document.getDocID(), nodeHandles.toArray(new HGHandle[nodeHandles.size()]));
        graph.add(link);

        logger.debug("Exiting indexDocument() for document {}", document.getDocID());
        return termHandles;
    }

    private Set<HGHandle> indexEntities(Document document) {
        logger.debug("Entering indexEntities() for document {}", document.getDocID());

        Set<HGHandle> entities = new HashSet<>();

        Map<String, Set<String>> edges = document.getTriples().stream()
                .collect(Collectors.groupingBy(
                        Triple::getObject,
                        Collectors.mapping(Triple::getSubject, Collectors.toSet())));

        for (Map.Entry<String, Set<String>> entry : edges.entrySet()) {
            List<HGHandle> handles = new ArrayList<>();

            Node node = new EntityNode(entry.getKey());
            HGHandle handle = nodeCache.get(node);
            if (handle == null) {
                handle = assertAtom(graph, node);
                handles.add(handle);
                nodeCache.put(node, handle);
            }

            for (String target : entry.getValue()) {
                node = new EntityNode(target);
                handle = nodeCache.get(node);
                if (handle == null) {
                    handle = assertAtom(graph, node);
                    handles.add(handle);
                    nodeCache.put(node, handle);
                }
            }

            RelatedToEdge link = new RelatedToEdge(handles.toArray(new HGHandle[handles.size()]));
            graph.add(link);

            entities.addAll(handles);
        }

        logger.debug("Exiting indexEntities() for document {}", document.getDocID());
        return entities;
    }

    private void linkTextAndKnowledge(Set<HGHandle> termHandles, Set<HGHandle> entityHandles) {
        logger.debug("Entering linkTextAndKnowledge()");

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

            handles.add(entityHandle);

            ContainedInEdge link = new ContainedInEdge(handles.toArray(new HGHandle[handles.size()]));
            graph.add(link);
        }

        logger.debug("Exiting linkTextAndKnowledge()");
    }

    public void index(Document document) throws IOException {
        if (batchStartTime == null) batchStartTime = System.currentTimeMillis();

        Set<HGHandle> entityHandles = indexEntities(document);
        Set<HGHandle> termHandles = indexDocument(document, entityHandles);
        linkTextAndKnowledge(termHandles, entityHandles);

        if (batch && ++indexedCounter % TRANSACTION_SIZE == 0) {
            logger.info(
                    "{} indexed documents, committing batch of {} documents ({} ms)",
                    indexedCounter, TRANSACTION_SIZE, System.currentTimeMillis() - batchStartTime);
            graph.getTransactionManager().commit();
            graph.runMaintenance();
            batchStartTime = System.currentTimeMillis();
            graph.getTransactionManager().beginTransaction();
        }
    }


    private Map<String, HGHandle> getQueryTermNodes(List<String> terms) {
        Map<String, HGHandle> termNodeMap = new HashMap<>();

        for (String term : terms) {
            HGHandle termNode = graph.findOne(
                    and(
                            type(TermNode.class),
                            eq("name", term)
                    )
            );

            if (termNode != null) termNodeMap.put(term, termNode);
        }

        return termNodeMap;
    }

    private Set<HGHandle> getSeedNodes(Map<String, HGHandle> queryTermNodes) {
        Set<HGHandle> seedNodes = new HashSet<>();

        for (HGHandle queryTermNode : queryTermNodes.values()) {
            Set<HGHandle> localSeedNodes = new HashSet<>();

            HGSearchResult<HGHandle> rs = graph.find(
                    and(
                            type(ContainedInEdge.class),
                            link(queryTermNode)
                    )
            );

            try {
                while (rs.hasNext()) {
                    HGHandle current = rs.next();
                    ContainedInEdge link = graph.get(current);
                    for (int i = 0; i < link.getArity(); i++) {
                        Node node = graph.get(link.getTargetAt(i));
                        if (node instanceof EntityNode) {
                            localSeedNodes.add(link.getTargetAt(i));
                        }
                    }
                }

                if (localSeedNodes.isEmpty()) {
                    localSeedNodes.add(queryTermNode);
                }

                seedNodes.addAll(localSeedNodes);
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

    public void getAllPaths(HGHandle source, HGHandle target) {
        HGDepthFirstTraversal traversal = new HGDepthFirstTraversal(source, new SimpleALGenerator(graph));

        while (traversal.hasNext()) {
            Pair<HGHandle, HGHandle> current = traversal.next();
            HGLink link = graph.get(current.getFirst());
            Object atom = graph.get(current.getSecond());
            System.out.println("Visiting atom " + atom + " pointed to by " + link);
        }
    }

    public double entityWeight(HGHandle entity, Set<HGHandle> seedNodes) {
        //double score = confidenceWeight(entity, seedNodes) * 1d/seedNodes.size() *

        // get all paths between the entity and a seed node (within a maximum distance)
        // constrained (by max distance) depth first search?
        HGHandle seedNode = seedNodes.iterator().next();
        getAllPaths(entity, seedNode);

        return 0d;
    }

    public void search(String query) throws IOException {
        List<String> tokens = tokenize(query);

        Map<String, HGHandle> queryTermNodes = getQueryTermNodes(tokens);

        Set<HGHandle> seedNodes = getSeedNodes(queryTermNodes);
        //System.out.println(seedNodes.stream().map(graph::get).collect(Collectors.toList()));

        /*double coverage = coverage(
                graph.findOne(
                        and(
                                type(EntityNode.class),
                                eq("name", "Semantic search")
                        )
                ),
                seedNodes
        );
        System.out.println(coverage);*/

        //HGHandle seedNode = seedNodes.iterator().next();
        //System.out.println("Source: " + graph.get(seedNode).toString());
        //double weight = confidenceWeight(seedNode, new HashSet<>(queryTermNodes.values()));
        //System.out.println("Weight: " + weight);

        entityWeight(graph.findOne(and(type(EntityNode.class), eq("name", "Search engine technology"))), seedNodes);
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
        HGSearchResult<HGHandle> rs = graph.find(
                or(
                        type(TermNode.class),
                        type(EntityNode.class)
                )
        );

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
                List<Node> edgeNodes = new ArrayList<>();
                for (int i = 0; i < edge.getArity(); i++) {
                    edgeNodes.add(graph.get(edge.getTargetAt(i)));
                }
                String members = String.join(" -- ", edgeNodes.stream()
                        .map(Node::toString)
                        .collect(Collectors.toList()));
                System.out.println(members + " - " + edge.getClass().getSimpleName());
            }
        } finally {
            rs.close();
        }
    }
}
