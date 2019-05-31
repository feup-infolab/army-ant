package armyant.hgoe.algorithms;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.stream.IntStream;

import armyant.Engine;
import grph.in_memory.InMemoryGrph;
import grph.path.Path;
import it.unimi.dsi.fastutil.booleans.BooleanOpenHashSet;
import it.unimi.dsi.fastutil.booleans.BooleanSet;
import it.unimi.dsi.fastutil.ints.Int2FloatMap;
import it.unimi.dsi.fastutil.ints.Int2FloatOpenHashMap;
import it.unimi.dsi.fastutil.ints.Int2IntMap;
import it.unimi.dsi.fastutil.ints.Int2IntOpenHashMap;
import it.unimi.dsi.fastutil.ints.IntIterator;
import it.unimi.dsi.fastutil.ints.IntOpenHashSet;
import it.unimi.dsi.fastutil.ints.IntSet;

/**
 * Created by José Devezas
 * 2019-05-31
 *
 * This is an implementation/adaptation of the Shortest Path Ant Colony Optimization algorithm:
 *
 * Gła̢bowski, M., Musznicki, B., Nowak, P., & Zwierzykowski, P. (2012). Shortest path problem solving based on ant
 * colony optimization metaheuristic. Image Processing & Communications, 17(1-2), 7-17.
 */
// FIXME unfinished
public class ShortestPathACOAlgorithm {
    private InMemoryGrph graph;
    private int m;          // number of ants
    private float alpha;    // influence of the pheromones
    private float beta;     // influence of the remaining data
    private float rho;      // speed of evaporation [0, 1]
    private float tauZero;  // initial level of pheromones
    private float tauMin;   // min level of pheromones
    private float tauMax;   // max level of pheromones
    private int s;          // source vertex
    private int t;          // target vertex

    private int C;          // maximum cost of an edge (weight) / ignored for now; treated as unweighted
    private int length;
    private int time;

    private Int2FloatMap edgeIDToTau;
    private IntSet[] visitedEdgesPerAnt;
    private IntSet[] visitedNodesPerAnt;
    private List<List<Path>> antPaths;

    public ShortestPathACOAlgorithm(
            InMemoryGrph graph, int m, float alpha, float beta, float rho,
            float tauZero, float tauMin, float tauMax, int s, int t) {
        this.graph = graph;
        this.m = m;
        this.alpha = alpha;
        this.beta = beta;
        this.rho = rho;
        this.tauZero = tauZero;
        this.tauMin = tauMin;
        this.tauMax = tauMax;
        this.s = s;
        this.t = t;

        init();
    }

    public void init() {
        C = 0;
        edgeIDToTau = new Int2FloatOpenHashMap();

        IntIterator sourceIterator = graph.getVertices().iterator();
        IntIterator targetIterator = graph.getVertices().iterator();
        while (sourceIterator.hasNext()) {
            int i = sourceIterator.nextInt();

            while (targetIterator.hasNext()) {
                int j = targetIterator.nextInt();

                for (int edgeID : graph.getEdgesConnecting(i, j)) {
                    edgeIDToTau.put(edgeID, tauZero);
                    C = 1; // unweighted hypergraph
                }
            }
        }

        length = C * (graph.getNumberOfVertices() - 1);
        time = 0;

        visitedEdgesPerAnt = new IntSet[m];
        visitedNodesPerAnt = new IntSet[m];
        antPaths = new ArrayList<>();
        IntStream.range(0, m).forEach(k -> {
            visitedEdgesPerAnt[k] = new IntOpenHashSet();
            visitedNodesPerAnt[k] = new IntOpenHashSet();
            antPaths.set(k, new ArrayList<>());
        });
    }

    public float computeCoefficient(int edgeID, int antK) {
        if (edgeIDToTau.get(edgeID) == 0) {
            return 1; // (1 / a_ij)^alpha
        } else {
            if (true) {

            } else {
                return edgeIDToTau.get(edgeID) * alpha + (1 - alpha) * 1;
            }
        }

        return 0f;
    }

    public Integer selectNextEdge(int sourceNodeID, int antK) {
        if (graph.getOutEdges(sourceNodeID).isEmpty()) return null;

        float best = -1;
        Integer result = null;

        IntIterator edgeIterator = graph.getOutEdges(sourceNodeID).iterator();
        while (edgeIterator.hasNext()) {
            int edgeID = edgeIterator.nextInt();
            if (!visitedNodesPerAnt[antK].contains(edgeID)) {
                float current = computeCoefficient(edgeID, antK);
                if (current > best) {
                    best = current;
                    result = edgeID;
                } else if (current == best && Engine.random() > 0.5) {
                    result = edgeID;
                }
            }
        }

        return result;
    }
}