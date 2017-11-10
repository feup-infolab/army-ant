package armyant.hgoe.indisk.traversals;

import armyant.hgoe.indisk.edges.Edge;
import org.hypergraphdb.HGHandle;
import org.hypergraphdb.HGRandomAccessResult;
import org.hypergraphdb.HyperGraph;

import java.util.*;

/**
 * Created by jldevezas on 2017-11-08.
 */
public class AllPaths {
    private HyperGraph graph;
    private HGHandle sourceHandle;
    private HGHandle targetHandle;
    private Integer maxDistance;

    private List<List<HGHandle>> paths;

    private Stack<HGHandle> path;
    private Set<HGHandle> onPath;

    public AllPaths(HyperGraph graph, HGHandle sourceHandle, HGHandle targetHandle) {
        this(graph, sourceHandle, targetHandle, null);
    }

    public AllPaths(HyperGraph graph, HGHandle sourceHandle, HGHandle targetHandle, Integer maxDistance) {
        this.graph = graph;
        this.sourceHandle = sourceHandle;
        this.targetHandle = targetHandle;
        this.maxDistance = maxDistance;

        this.paths = new ArrayList<>();

        this.path = new Stack<>();
        this.onPath = new HashSet<>();
    }

    public List<List<HGHandle>> getPaths() {
        return paths;
    }

    private Set<HGHandle> getNeighborEdges(HGHandle sourceEdgeHandle) {
        Set<HGHandle> edges = new HashSet<>();

        Edge sourceEdge = graph.get(sourceEdgeHandle);

        for (HGHandle nodeHandle : sourceEdge.getTail()) {
            HGRandomAccessResult<HGHandle> incidentEdgeHandles = graph.getIncidenceSet(nodeHandle).getSearchResult();
            while (incidentEdgeHandles.hasNext()) {
                edges.add(incidentEdgeHandles.next());
            }
            //armyant.hgoe.inmemory.edges.addAll(graph.findAll(incident(nodeHandle)));
        }

        return edges;
    }

    public void traverse() {
        HGRandomAccessResult<HGHandle> incidenceEdgeHandles = graph.getIncidenceSet(sourceHandle).getSearchResult();
        while (incidenceEdgeHandles.hasNext()) {
            traverse(incidenceEdgeHandles.next());
        }
    }

    protected void traverse(HGHandle fromEdgeHandle) {
        path.push(fromEdgeHandle);
        onPath.add(fromEdgeHandle);

        Edge fromEdge = graph.get(fromEdgeHandle);

        if (fromEdge.getTail().contains(targetHandle)) {
            paths.add(new ArrayList<>(path));
        } else {
            for (HGHandle neighborEdge : getNeighborEdges(fromEdgeHandle)) {
                if (maxDistance != null && path.size() >= maxDistance) break;
                if (!onPath.contains(neighborEdge)) traverse(neighborEdge);
            }
        }

        path.pop();
        onPath.remove(fromEdgeHandle);
    }
}
