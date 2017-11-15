package armyant.hgoe.inmemory;

import edu.uci.ics.jung.graph.Hypergraph;
import edu.uci.ics.jung.graph.util.EdgeType;
import es.usc.citius.hipster.graph.DirectedEdge;
import es.usc.citius.hipster.graph.GraphEdge;
import es.usc.citius.hipster.graph.HipsterGraph;
import es.usc.citius.hipster.graph.UndirectedEdge;
import es.usc.citius.hipster.util.F;

import java.util.ArrayList;
import java.util.Collection;
import java.util.Collections;
import java.util.List;
import java.util.stream.Collectors;

/**
 * Created by jldevezas on 2017-11-15.
 */
public class JUNGHipsterHypergraphAdapter<V,E> implements HipsterGraph<V,E> {
    protected Hypergraph<V,E> graph;

    public JUNGHipsterHypergraphAdapter(Hypergraph<V, E> graph) {
        this.graph = graph;
    }

    protected List<GraphEdge<V,E>> adapt(final Collection<E> edges){
        /*return edges.stream().flatMap(edge -> {
            graph.getIncidentVertices(edge).stream();
            for (V source : vertices) {
                for (V target : vertices) {
                    if (!source.equals(target)) {
                        return new UndirectedEdge<>(source, target, 1);
                    }
                }
            }
        }).collect(Collectors.toList());*/
        return new ArrayList<>();
    }

    @Override
    public Iterable<GraphEdge<V, E>> edges() {
        final Collection<E> edges = graph.getEdges();
        if (edges == null || edges.isEmpty()){
            return Collections.emptyList();
        }
        return adapt(edges);
    }

    @Override
    public Iterable<V> vertices() {
        return graph.getVertices();
    }

    @Override
    public Iterable<GraphEdge<V, E>> edgesOf(V vertex) {
        final Collection<E> edges = graph.getIncidentEdges(vertex);
        if (edges == null || edges.isEmpty()){
            return Collections.emptyList();
        }
        return adapt(edges);
    }

}