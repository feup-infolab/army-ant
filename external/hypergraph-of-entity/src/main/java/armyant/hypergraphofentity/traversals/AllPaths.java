package armyant.hypergraphofentity.traversals;

import armyant.hypergraphofentity.edges.Edge;
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

    private List<List<HGHandle>> paths;

    private Stack<HGHandle> path;
    private Set<HGHandle> onPath;

    public AllPaths(HyperGraph graph, HGHandle sourceHandle, HGHandle targetHandle) {
        this.graph = graph;
        this.sourceHandle = sourceHandle;
        this.targetHandle = targetHandle;

        this.paths = new ArrayList<>();

        this.path = new Stack<>();
        this.onPath = new HashSet<>();
    }

    public List<List<HGHandle>> getPaths() {
        return paths;
    }

    public void traverse() {
        traverse(sourceHandle);
    }

    protected void traverse(HGHandle fromNode) {
        if (fromNode.equals(targetHandle)) {
            paths.add(path);
        } else {
            HGRandomAccessResult<HGHandle> incidentEdges = graph.getIncidenceSet(fromNode).getSearchResult();
            while (incidentEdges.hasNext()) {
                HGHandle edgeHandle = incidentEdges.next();
                Edge edge = graph.get(edgeHandle);
                //if (edge.getTail().contains())
                if (!onPath.contains(edgeHandle)) traverse(edgeHandle);
            }
        }
    }
}
