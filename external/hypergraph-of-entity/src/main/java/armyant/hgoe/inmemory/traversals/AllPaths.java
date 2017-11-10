package armyant.hgoe.inmemory.traversals;

import armyant.hgoe.inmemory.edges.Edge;
import armyant.hgoe.inmemory.nodes.Node;
import edu.uci.ics.jung.graph.SetHypergraph;
import org.hypergraphdb.HGHandle;
import org.hypergraphdb.HGRandomAccessResult;
import org.hypergraphdb.HyperGraph;

import java.util.*;

/**
 * Created by jldevezas on 2017-11-08.
 */
public class AllPaths {
    private SetHypergraph<Node, Edge> graph;
    private Node sourceNode;
    private Node targetNode;
    private Integer maxDistance;

    private List<List<Edge>> paths;

    private Stack<Edge> path;
    private Set<Edge> onPath;

    public AllPaths(SetHypergraph<Node, Edge> graph, Node sourceNode, Node targetNode) {
        this(graph, sourceNode, targetNode, null);
    }

    public AllPaths(SetHypergraph<Node, Edge> graph, Node sourceNode, Node targetNode, Integer maxDistance) {
        this.graph = graph;
        this.sourceNode = sourceNode;
        this.targetNode = targetNode;
        this.maxDistance = maxDistance;

        this.paths = new ArrayList<>();

        this.path = new Stack<>();
        this.onPath = new HashSet<>();
    }

    public List<List<Edge>> getPaths() {
        return paths;
    }

    private Set<Edge> getNeighborEdges(Edge sourceEdge) {
        Set<Edge> edges = new HashSet<>();

        for (Node node : graph.getIncidentVertices(sourceEdge)) {
            edges.addAll(graph.getIncidentEdges(node));
        }

        return edges;
    }

    public void traverse() {
        for (Edge edge : graph.getIncidentEdges(sourceNode)) {
            traverse(edge);
        }
    }

    protected void traverse(Edge fromEdge) {
        path.push(fromEdge);
        onPath.add(fromEdge);

        if (graph.getIncidentVertices(fromEdge).contains(targetNode)) {
            paths.add(new ArrayList<>(path));
        } else {
            for (Edge neighborEdge : getNeighborEdges(fromEdge)) {
                if (maxDistance != null && path.size() >= maxDistance) break;
                if (!onPath.contains(neighborEdge)) traverse(neighborEdge);
            }
        }

        path.pop();
        onPath.remove(fromEdge);
    }
}
