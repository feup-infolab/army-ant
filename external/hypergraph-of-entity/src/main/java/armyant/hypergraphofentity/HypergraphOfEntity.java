package armyant.hypergraphofentity;

import armyant.hypergraphofentity.edges.ContainedInEdge;
import armyant.hypergraphofentity.edges.DocumentEdge;
import armyant.hypergraphofentity.edges.RelatedToEdge;
import armyant.hypergraphofentity.nodes.DocumentNode;
import armyant.hypergraphofentity.nodes.EntityNode;
import armyant.hypergraphofentity.nodes.Node;
import armyant.hypergraphofentity.nodes.TermNode;
import org.apache.lucene.analysis.standard.StandardTokenizer;
import org.apache.lucene.analysis.tokenattributes.CharTermAttribute;
import org.apache.lucene.util.AttributeFactory;
import org.hypergraphdb.*;
import org.hypergraphdb.algorithms.HGDepthFirstTraversal;
import org.hypergraphdb.algorithms.SimpleALGenerator;
import org.hypergraphdb.util.Pair;

import java.io.IOException;
import java.io.StringReader;
import java.util.*;
import java.util.stream.Collectors;

import static org.hypergraphdb.HGQuery.hg.*;

/**
 * Created by jldevezas on 2017-10-23.
 */
public class HypergraphOfEntity {

    private String path;
    private HyperGraph graph;

    public HypergraphOfEntity(String path) {
        this.path = path;

        HGConfiguration config = new HGConfiguration();
        config.setTransactional(false);
        config.setSkipOpenedEvent(true);

        this.graph = HGEnvironment.get(this.path, config);
    }

    public void close() {
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
        List<String> tokens = tokenize(document.getText());

        Set<HGHandle> nodeHandles = new HashSet<>();
        Set<HGHandle> termHandles = new HashSet<>();

        DocumentNode documentNode = new DocumentNode(document.getDocID());
        nodeHandles.add(addUnique(graph, documentNode, eq(documentNode)));

        nodeHandles.addAll(entityHandles);

        for (String term : tokens) {
            Node node = new TermNode(term);
            HGHandle handle = addUnique(graph, node, eq(node));
            nodeHandles.add(handle);
            termHandles.add(handle);
        }

        DocumentEdge link = new DocumentEdge(document.getDocID(), nodeHandles.toArray(new HGHandle[nodeHandles.size()]));
        graph.add(link);

        return termHandles;
    }

    private Set<HGHandle> indexEntities(Document document) {
        Set<HGHandle> entities = new HashSet<>();

        Map<String, Set<String>> edges = document.getTriples().stream()
                .collect(Collectors.groupingBy(
                        Triple::getObject,
                        Collectors.mapping(Triple::getSubject, Collectors.toSet())));

        for (Map.Entry<String, Set<String>> entry : edges.entrySet()) {
            List<HGHandle> handles = new ArrayList<>();

            Node node = new EntityNode(entry.getKey());
            handles.add(addUnique(graph, node, eq(node)));

            for (String target : entry.getValue()) {
                node = new EntityNode(target);
                handles.add(addUnique(graph, node, eq(node)));
            }

            RelatedToEdge link = new RelatedToEdge(handles.toArray(new HGHandle[handles.size()]));
            graph.add(link);

            entities.addAll(handles);
        }

        return entities;
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

            handles.add(entityHandle);

            ContainedInEdge link = new ContainedInEdge(handles.toArray(new HGHandle[handles.size()]));
            graph.add(link);
        }
    }

    public void index(Document document) throws IOException {
        Set<HGHandle> entityHandles = indexEntities(document);
        Set<HGHandle> termHandles = indexDocument(document, entityHandles);
        linkTextAndKnowledge(termHandles, entityHandles);
    }

    private Set<Node> getSeedNodes(List<String> terms) {
        Set<Node> seedNodes = new HashSet<>();

        for (String term : terms) {
            Set<Node> localSeedNodes = new HashSet<>();

            HGHandle queryTermNodeHandle = graph.findOne(
                    and(
                            type(TermNode.class),
                            eq("name", term)
                    )
            );

            if (queryTermNodeHandle == null) continue;

            HGSearchResult<HGHandle> rs = graph.find(
                    and(
                            type(ContainedInEdge.class),
                            link(queryTermNodeHandle)
                    )
            );

            try {
                while (rs.hasNext()) {
                    HGHandle current = rs.next();
                    ContainedInEdge link = graph.get(current);
                    for (int i = 0; i < link.getArity(); i++) {
                        Node node = graph.get(link.getTargetAt(i));
                        if (node instanceof EntityNode) {
                            EntityNode entityNode = (EntityNode) node;
                            localSeedNodes.add(entityNode);
                        }
                    }
                }

                if (localSeedNodes.isEmpty()) {
                    localSeedNodes.add(graph.get(queryTermNodeHandle));
                }

                seedNodes.addAll(localSeedNodes);
            } finally {
                rs.close();
            }
        }

        return seedNodes;
    }

    public void search(String query) throws IOException {
        List<String> tokens = tokenize(query);
        System.out.println(getSeedNodes(tokens));
    }

    public void printDepthFirst(String fromNodeName) {
        HGHandle termNode = graph.findOne(and(type(TermNode.class), eq("name", fromNodeName)));

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
}
