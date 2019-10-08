package armyant.util;

import java.io.IOException;
import java.util.List;
import java.util.ListIterator;
import java.util.Map;
import java.util.stream.Collectors;

import org.jgrapht.Graph;
import org.jgrapht.alg.scoring.PageRank;
import org.jgrapht.graph.DefaultDirectedGraph;
import org.jgrapht.graph.DefaultEdge;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import armyant.Engine;

public class TextRank {
    private static final Logger logger = LoggerFactory.getLogger(TextRank.class);

    protected String text;
    protected Graph<String, DefaultEdge> graph;
    protected Map<String,Double> pageRank;

    public TextRank(String text) {
        this.text = text;
        this.graph = null;
        this.pageRank = null;
    }

    public void buildGraph() throws IOException {
        buildGraph(4);
    }

    public void buildGraph(int windowSize) throws IOException {
        //logger.debug("Building graph for TextRank, using windowSize = {} ", windowSize);

        this.graph = new DefaultDirectedGraph<>(DefaultEdge.class);

        List<String> tokens = Engine.analyze(text);

        for (ListIterator<String> startIt = tokens.listIterator(); startIt.hasNext(); startIt.next()) {
            int start = startIt.nextIndex();

            if (start+windowSize > tokens.size()) break;

            for (ListIterator<String> sourceIt = tokens.subList(start, start+windowSize).listIterator();
                    sourceIt.hasNext(); ) {
                int i = sourceIt.nextIndex();
                String source = sourceIt.next();

                if (!this.graph.containsVertex(source)) {
                    this.graph.addVertex(source);
                }

                for (ListIterator<String> targetIt = tokens.subList(start, start+windowSize).listIterator();
                        targetIt.hasNext(); ) {
                    int j = targetIt.nextIndex();
                    String target = targetIt.next();

                    if (i >= j) continue;

                    if (!this.graph.containsVertex(target)) {
                        this.graph.addVertex(target);
                    }

                    this.graph.addEdge(source, target);
                }
            }
        }
    }

    public void computePageRank() throws IOException {
        if (this.graph == null) buildGraph();

        //logger.debug("Computing PageRank for TextRank graph");
        PageRank<String,DefaultEdge> pageRank = new PageRank<>(this.graph);
        this.pageRank = pageRank.getScores();
    }

    public List<String> getKeywords() throws IOException {
        return getKeywords(0.05f);
    }

    public List<String> getKeywords(float ratio) throws IOException {
        if (this.pageRank == null) computePageRank();

        //logger.debug("Ranking keywords based on PageRank and retriving top {}%", Math.round(ratio * 100));
        return this.graph.vertexSet().stream()
            .sorted((a, b) -> Double.compare(pageRank.get(b), pageRank.get(a)))
            .limit(Math.round(this.graph.vertexSet().size() * ratio))
            .collect(Collectors.toList());
    }
}