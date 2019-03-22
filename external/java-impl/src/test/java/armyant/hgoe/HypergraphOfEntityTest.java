package armyant.hgoe;

import armyant.hgoe.edges.DocumentEdge;
import armyant.hgoe.edges.Edge;
import armyant.hgoe.exceptions.HypergraphException;
import armyant.hgoe.nodes.Node;
import armyant.hgoe.nodes.TermNode;
import armyant.structures.Document;
import armyant.structures.Entity;
import armyant.structures.Result;
import armyant.structures.ResultSet;
import armyant.structures.Triple;
import edu.mit.jwi.IRAMDictionary;
import edu.mit.jwi.RAMDictionary;
import edu.mit.jwi.data.ILoadPolicy;
import edu.mit.jwi.item.*;
import grph.Grph;
import grph.in_memory.InMemoryGrph;
import grph.path.ArrayListPath;
import grph.path.Path;
import grph.properties.NumericalProperty;
import it.unimi.dsi.fastutil.ints.IntSet;
import org.testng.annotations.Test;

import java.io.File;
import java.io.IOException;
import java.util.*;

/**
 * Created by jldevezas on 2017-11-29.
 */
@Test
public class HypergraphOfEntityTest {
    public static final Document document1 = new Document(
        "D1",

        "Semantic search",

        "Semantic search seeks to improve search accuracy by understanding the searcher's intent and the " +
        "contextual meaning of terms as they appear in the searchable dataspace, whether on the Web or within a " +
        "closed system, to generate more relevant results.",

        Arrays.asList(
                new Triple(
                        new Entity("http://example.com/Semantic_search", "Semantic search"),
                        new Entity("http://example.com/related_to", "related_to"),
                        new Entity("http://example.com/Search_engine_technology", "Search engine technology")
                ),
                new Triple(
                        new Entity("http://example.com/Semantic_search", "Semantic search"),
                        new Entity("http://example.com/related_to", "related_to"),
                        new Entity("http://example.com/Intention", "Intention")
                ),
                new Triple(
                        new Entity("http://example.com/Semantic_search", "Semantic search"),
                        new Entity("http://example.com/related_to", "related_to"),
                        new Entity("http://example.com/Context_(language_use)", "Context (language use)")
                ),
                new Triple(
                        new Entity("http://example.com/Semantic_search", "Semantic search"),
                        new Entity("http://example.com/related_to", "related_to"),
                        new Entity("http://example.com/World_Wide_Web", "World Wide Web")
                )
        )
    );
    public static final Document document2 = new Document(
        "D2",

        "Search engine technology",

        "A search engine is an information retrieval software program that discovers, crawls, transforms and " +
        "stores information for retrieval and presentation in response to user queries.",

        Arrays.asList(
                new Triple(
                        new Entity("http://example.org/Search_engine_technology", "Search engine technology"),
                        new Entity("http://example.org/related_to", "related_to"),
                        new Entity("http://example.org/Search_engine", "Search engine")
                )
        )
    );
    public static final Document document3 = new Document(
        "D3",

        "Unreachable",

        "Unreachable people.",

        Collections.singletonList(new Triple(
                new Entity("http://example.org/Unreachable_Me", "Unreachable Me"),
                new Entity("http://example.org/related_to", "related_to"),
                new Entity("http://example.org/Unreachable_You", "Unreachable You")
        ))
    );
    private static String dbPath = "/tmp/hgoe-inmemory";

    public void testIndex() throws Exception {
        HypergraphOfEntity hgoe = new HypergraphOfEntity(
                dbPath, new ArrayList<>(), null, true);
        hgoe.index(document1);
        hgoe.index(document2);
        hgoe.index(document3);
        hgoe.postProcessing();
        hgoe.save();
    }

    public void testSearch() throws IOException, HypergraphException {
        HypergraphOfEntity hgoe = new HypergraphOfEntity(dbPath);

        //ResultSet resultSet = hgoe.search("web search system");
        //ResultSet resultSet = hgoe.search("Monuments of India");
        //ResultSet resultSet = hgoe.search("Poirot");
        ResultSet resultSet = hgoe.search("national park", 0, 1000);
        //ResultSet resultSet = hgoe.search("viking");
        //ResultSet resultSet = hgoe.search("viking ship");

        while (resultSet.hasNext()) {
            Result result = resultSet.next();
            System.out.println(String.format("%.4f %s %s", result.getScore(), result.getID(), result.getName()));
        }
    }

    public void testTrace() throws IOException, HypergraphException {
        HypergraphOfEntity hgoe = new HypergraphOfEntity(dbPath);

        //ResultSet resultSet = hgoe.search("web search system");
        //ResultSet resultSet = hgoe.search("Monuments of India");
        //ResultSet resultSet = hgoe.search("Poirot");
        //ResultSet resultSet = hgoe.search("national park");
        //ResultSet resultSet = hgoe.search("viking");
        //ResultSet resultSet = hgoe.search("viking ship");
        ResultSet resultSet = hgoe.search("doom", 0, 1000);

        resultSet.getTrace().toASCII();
    }

    public void testContainsNode() throws HypergraphException {
        HypergraphOfEntity hgoe = new HypergraphOfEntity(dbPath);
        String[] terms = {"ca", "calif.", "drug"};
        for (String term : terms) {
            System.out.println(term + ": " + hgoe.containsNode(new TermNode(term)));
        }

    }

    public void testAtomInstanceOf() {
        Edge edge = new DocumentEdge();
        Atom atom = edge;
        assert atom instanceof RankableAtom;
        assert atom instanceof Edge;
        assert atom instanceof DocumentEdge;
        assert !(atom instanceof Node);
    }

    /**
     * Sandbox tests
     */

    // How does a Path work in Grph?
    public void testPath() {
        Path path = new ArrayListPath();
        path.setSource(10);
        path.extend(1, 20);
        path.extend(2, 10);
        path.extend(3, 20);
        path.extend(30);
        System.out.println("Path: " + path);
        System.out.println("Path length: " + path.getLength());
        System.out.println("Index of vertex 20: " + path.indexOfVertex(20));
        System.out.println("Edge leading to vertex 20: " + path.getEdgeHeadingToVertexAt(path.indexOfVertex(20)));
    }

    public void testWordNet() throws IOException {
        String[] terms = {"terms", "results", "system", "web", "meaning", "searcher", "understanding"};

        IRAMDictionary dict = new RAMDictionary(new File("/usr/share/wordnet"), ILoadPolicy.NO_LOAD);
        dict.open();

        for (String term : terms) {
            System.out.println(term);
            IIndexWord idxWord = dict.getIndexWord(term, POS.NOUN);
            if (idxWord != null) {
                IWordID wordID = idxWord.getWordIDs().get(0);
                IWord word = dict.getWord(wordID);
                ISynset synset = word.getSynset();

                for (IWord w : synset.getWords()) {
                    Set<String> syns = new HashSet<>(Arrays.asList(w.getLemma().toLowerCase().split("_")));
                    for (String syn : syns) {
                        System.out.println('\t' + syn);
                    }
                }
            }
        }

        dict.close();
    }

    // Can Grph support a hypergraph with both directed and undirected hyperedges?
    // How does traversal work in mixed hypergraphs? Difference between incident to, in and out edges.
    public void testMixedEdgeHypergraph() {
        Grph g = new InMemoryGrph();

        g.addNVertices(6);
        System.out.println("Vertices: " + g.getVertices());

        int outgoingDirectedEdgeID = g.getNextEdgeAvailable();
        g.addDirectedHyperEdge(outgoingDirectedEdgeID);

        int undirectedEdgeID = g.getNextEdgeAvailable();
        g.addUndirectedHyperEdge(undirectedEdgeID);

        int incomingDirectedEdgeID = g.getNextEdgeAvailable();
        g.addDirectedHyperEdge(incomingDirectedEdgeID);

        // {0,1} -> {2}
        g.addToDirectedHyperEdgeTail(outgoingDirectedEdgeID, 0);
        g.addToDirectedHyperEdgeTail(outgoingDirectedEdgeID, 1);
        g.addToDirectedHyperEdgeHead(outgoingDirectedEdgeID, 2);

        // {0,1,3,4}
        Arrays.stream(new Integer[]{0, 1, 3, 4}).forEach(n -> g.addToUndirectedHyperEdge(1, n));

        // {2,3,4} -> {0,5}
        g.addToDirectedHyperEdgeTail(incomingDirectedEdgeID, 2);
        g.addToDirectedHyperEdgeTail(incomingDirectedEdgeID, 3);
        g.addToDirectedHyperEdgeTail(incomingDirectedEdgeID, 4);
        g.addToDirectedHyperEdgeHead(incomingDirectedEdgeID, 0);
        g.addToDirectedHyperEdgeHead(incomingDirectedEdgeID, 5);

        IntSet n0IncidentToEdges = g.getEdgesIncidentTo(0);
        System.out.println("Node 0 incident to edges: " + n0IncidentToEdges);
        assert n0IncidentToEdges.equals(new HashSet<>(Arrays.asList(
                outgoingDirectedEdgeID, incomingDirectedEdgeID, undirectedEdgeID)));

        IntSet undirectedEdgeNodes = g.getUndirectedHyperEdgeVertices(undirectedEdgeID);
        System.out.println("Node 0 through undirected: " + undirectedEdgeNodes);
        assert undirectedEdgeNodes.equals(new HashSet<>(Arrays.asList(0, 1, 3, 4)));

        IntSet directedEdgeTailNodes = g.getDirectedHyperEdgeTail(outgoingDirectedEdgeID);
        System.out.println("Node 0 through directed (tail): " + directedEdgeTailNodes);
        assert directedEdgeTailNodes.equals(new HashSet<>(Arrays.asList(0, 1)));

        IntSet directedEdgeHeadNodes = g.getDirectedHyperEdgeHead(outgoingDirectedEdgeID);
        System.out.println("Node 0 through directed (head): " + directedEdgeHeadNodes);
        assert directedEdgeHeadNodes.equals(new HashSet<>(Collections.singletonList(2)));

        IntSet n0InEdges = g.getInEdges(0);
        System.out.println("Node 0 in edges: " + n0InEdges);
        assert n0InEdges.equals(new HashSet<>(Arrays.asList(incomingDirectedEdgeID, undirectedEdgeID)));
        assert !n0InEdges.contains(outgoingDirectedEdgeID);

        IntSet n0OutEdges = g.getOutEdges(0);
        System.out.println("Node 0 out edges: " + n0OutEdges);
        assert n0OutEdges.equals(new HashSet<>(Arrays.asList(outgoingDirectedEdgeID, undirectedEdgeID)));
        assert !n0OutEdges.contains(incomingDirectedEdgeID);

        IntSet outgoingDirectedEdgeIncidentToNodes = g.getVerticesIncidentToEdge(outgoingDirectedEdgeID);
        System.out.println("Outgoing edge incident nodes: " + outgoingDirectedEdgeIncidentToNodes);
        assert outgoingDirectedEdgeIncidentToNodes.equals(new HashSet<>(Arrays.asList(0, 1, 2)));

        IntSet incomingDirectedEdgeIncidentToNodes = g.getVerticesIncidentToEdge(incomingDirectedEdgeID);
        System.out.println("Incoming edge incident nodes: " + incomingDirectedEdgeIncidentToNodes);
        assert incomingDirectedEdgeIncidentToNodes.equals(new HashSet<>(Arrays.asList(2, 3, 4, 0, 5)));

        // XXX getVerticesIncidentToEdge() does not work in undirected edges
        IntSet undirectedEdgeIncidentToNodes = g.getUndirectedHyperEdgeVertices(undirectedEdgeID);
        System.out.println("Undirected edge nodes: " + undirectedEdgeIncidentToNodes);
        assert undirectedEdgeIncidentToNodes.equals(new HashSet<>(Arrays.asList(0, 1, 3, 4)));

        // Default: DIRECTION.in_out + includes all nodes in undirected edges with this node.
        IntSet n2Neighbors = g.getNeighbours(2);
        System.out.println("Node 2 neighbors: " + n2Neighbors);
        assert n2Neighbors.equals(new HashSet<>(Arrays.asList(0, 1, 5)));

        // The degree of a node is the number of edges that contain it.
        int n2Degree = g.getVertexDegree(2);
        assert n2Degree == 3;

        int previousNumVertices = g.getNumberOfVertices();
        int previousNumEdges = g.getNumberOfEdges();
        int removeNodeID = 2;
        for (int edgeID : g.getEdgesIncidentTo(removeNodeID)) {
            if (g.isDirectedHyperEdge(edgeID)) {
                if (g.getDirectedHyperEdgeTail(edgeID).contains(removeNodeID)) {
                    g.removeFromDirectedHyperEdgeTail(edgeID, removeNodeID);
                    if (g.getDirectedHyperEdgeTail(edgeID).size() == 0) g.removeEdge(edgeID);
                } else {
                    g.removeFromDirectedHyperEdgeHead(edgeID, removeNodeID);
                    if (g.getDirectedHyperEdgeHead(edgeID).size() == 0) g.removeEdge(edgeID);
                }
            } else {
                g.removeFromHyperEdge(edgeID, removeNodeID);
                if (g.getUndirectedHyperEdgeVertices(edgeID).size() == 0) g.removeEdge(edgeID);
            }
        }
        g.removeVertex(removeNodeID);
        assert g.getNumberOfVertices() == previousNumVertices - 1;
        assert g.getNumberOfEdges() == previousNumEdges - 1;

        NumericalProperty weights = new NumericalProperty("weight");
        float n0Weight = 0.1f;
        float n1Weight = (float) Math.max(0, Math.log10((2000 - 500) / 500));
        weights.setValue(0, n0Weight);
        weights.setValue(1, n1Weight);
        assert weights.getValueAsFloat(0) == n0Weight;
        assert weights.getValueAsFloat(1) == n1Weight;
        System.out.println(String.format("weight(n0) = %.2f", n0Weight));
        System.out.println(String.format("weight(n1) = %.2f", n1Weight));

        /**
         * Summary
         *
         * getEdgesIncidentTo(vertex) => all linked edges are included
         * getVerticesIncidentToEdge(edge) => only works for directed hyperedges, but includes all in+out nodes;
         *  must use getUndirectedHyperEdgeVertices(edge) for undirected hyperedges.
         *
         * getNeighbors => defaults to all neighbors based on directed and undirected edges, ignoring direction.
         *
         * getOutEdges => includes directed outgoing edges and all undirected edges.
         * getInEdges => includes directed incoming edges and all undirected edges.
         */
    }
}
