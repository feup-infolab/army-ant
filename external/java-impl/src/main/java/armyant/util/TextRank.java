package armyant.util;

import java.io.IOException;
import java.util.List;
import java.util.ListIterator;
import java.util.Random;
import java.util.stream.Collectors;

import org.apache.commons.collections4.BidiMap;
import org.apache.commons.collections4.bidimap.DualHashBidiMap;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import armyant.Engine;
import grph.algo.distance.PageRank;
import grph.in_memory.InMemoryGrph;
import grph.properties.ObjectProperty;
import grph.properties.StringProperty;

public class TextRank {
    private static final Logger logger = LoggerFactory.getLogger(TextRank.class);

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
        buildGraph(4);
    }

    public void buildGraph(int windowSize) throws IOException {
        //logger.debug("Building graph for TextRank, using windowSize = {} ", windowSize);

        this.graph = new InMemoryGrph();

        List<String> tokens = Engine.analyze(text);

        for (ListIterator<String> startIt = tokens.listIterator(); startIt.hasNext(); startIt.next()) {
            int start = startIt.nextIndex();

            if (start+windowSize > tokens.size()) break;

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

                    if (i >= j) continue;

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

        //logger.debug("Computing PageRank for TextRank graph");
        this.pageRank = graph.getPageRanking(new Random());
        this.pageRank.compute();
    }

    public List<String> getKeywords() throws IOException {
        return getKeywords(0.05f);
    }

    public List<String> getKeywords(float ratio) throws IOException {
        if (this.pageRank == null) computePageRank();

        //logger.debug("Ranking keywords based on PageRank and retriving top {}%", Math.round(ratio * 100));
        return this.graph.getVertices().stream()
            .sorted((a, b) -> Double.compare(pageRank.getRank(b), pageRank.getRank(a)))
            .limit(Math.round(this.graph.getNumberOfVertices() * ratio))
            .map(this.nodeIndex::getKey)
            .collect(Collectors.toList());
    }
}