package armyant.util;

import java.io.IOException;
import java.util.HashMap;
import java.util.List;
import java.util.ListIterator;
import java.util.Map;
import java.util.Random;
import java.util.stream.Collectors;

import org.apache.commons.collections4.bidimap.DualHashBidiMap;
import org.apache.commons.collections4.BidiMap;

import armyant.Engine;
import armyant.structures.Document;
import grph.algo.distance.PageRank;
import grph.in_memory.InMemoryGrph;

public class TextRank {
    protected String text;
    protected InMemoryGrph graph;
    protected PageRank pageRank;

    protected BidiMap<String, Integer> nodeIndex;

    public TextRank(String text) {
        this.text = text;
        this.graph = null;
        this.pageRank = null;
        this.nodeIndex = new DualHashBidiMap<>();
    }

    public void buildGraph() throws IOException {
        buildGraph(4, 0.05f);
    }

    public void buildGraph(int windowSize, float ratio) throws IOException {
        this.graph = new InMemoryGrph();

        List<String> tokens = Engine.analyze(text);

        for (ListIterator<String> startIt = tokens.listIterator(); startIt.hasNext(); startIt.next()) {
            int start = startIt.nextIndex();

            for (ListIterator<String> sourceIt = tokens.subList(start, start+windowSize).listIterator(); sourceIt.hasNext(); ) {
                int i = sourceIt.nextIndex();
                String source = sourceIt.next();
                Integer sourceNodeID = nodeIndex.get(source);

                if (sourceNodeID == null) {
                    sourceNodeID = this.graph.addVertex();
                    this.nodeIndex.put(source, sourceNodeID);
                }

                for (ListIterator<String> targetIt = tokens.subList(start, start+windowSize).listIterator(); targetIt.hasNext(); ) {
                    int j = targetIt.nextIndex();
                    String target = targetIt.next();
                    Integer targetNodeID = nodeIndex.get(target);

                    if (targetNodeID == null) {
                        targetNodeID = this.graph.addVertex();
                        this.nodeIndex.put(target, targetNodeID);
                    }

                    this.graph.addSimpleEdge(sourceNodeID, targetNodeID, false);
                }
            }
        }
    }

    public void computePageRank() throws IOException {
        if (this.graph == null) buildGraph();
        this.pageRank = graph.getPageRanking(new Random());
        this.pageRank.compute();
    }

    public List<String> getKeywords() throws IOException {
        if (this.pageRank == null) computePageRank();
        return this.graph.getVertices().stream()
            .sorted((a, b) -> Double.compare(pageRank.getRank(b), pageRank.getRank(a)))
            .map(this.nodeIndex::getKey)
            .collect(Collectors.toList());
    }
}