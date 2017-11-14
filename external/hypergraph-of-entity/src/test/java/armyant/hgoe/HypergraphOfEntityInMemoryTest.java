package armyant.hgoe;

import armyant.hgoe.inmemory.HypergraphOfEntityInMemory;
import armyant.hgoe.structures.Document;
import armyant.hgoe.structures.Result;
import armyant.hgoe.structures.ResultSet;
import armyant.hgoe.structures.Triple;
import org.testng.annotations.Test;

import java.io.IOException;
import java.util.Arrays;
import java.util.Collections;

/**
 * Created by jldevezas on 2017-10-23.
 */
@Test
public class HypergraphOfEntityInMemoryTest {

    public static final Document document1 = new Document(
            "D1",

            "Semantic search seeks to improve search accuracy by understanding the searcher's intent and the " +
            "contextual meaning of terms as they appear in the searchable dataspace, whether on the Web or within a " +
            "closed system, to generate more relevant results.",

            Arrays.asList(
                    new Triple("Semantic search", "related_to", "Search engine technology"),
                    new Triple("Semantic search", "related_to", "Intention"),
                    new Triple("Semantic search", "related_to", "Context (language use)"),
                    new Triple("Semantic search", "related_to", "World Wide Web")
            )
    );

    public static final Document document2 = new Document(
            "D2",

            "A search engine is an information retrieval software program that discovers, crawls, transforms and " +
            "stores information for retrieval and presentation in response to user queries.",

            Arrays.asList(
                    new Triple("Search engine technology", "related_to", "Search engine")
            )
    );

    public static final Document document3 = new Document(
            "D3",

            "Unreachable people.",

            Collections.singletonList(new Triple("Unreachable Me", "related_to", "Unreachable You"))
    );

    private String dbPath = "/tmp/test-hgoe-inmemory";

    public void testPrints() {
        HypergraphOfEntityInMemory hgoe = new HypergraphOfEntityInMemory(dbPath);

        System.out.println("====> Statistics");
        hgoe.printStatistics();
        System.out.print("\n");

        System.out.println("====> Nodes");
        hgoe.printNodes();
        System.out.print("\n");

        System.out.println("====> Edges");
        hgoe.printEdges();
        System.out.print("\n");

        /*System.out.println("====> Depth first traversal starting at 'Semantic search' entity");
        hgoe.printDepthFirst("Semantic search");
        System.out.print("\n");*/

        //hgoe.printDepthFirst("web");
    }

    public void testIndex() throws IOException {
        HypergraphOfEntityInMemory hgoe = new HypergraphOfEntityInMemory(dbPath, true);
        hgoe.index(document1);
        hgoe.index(document2);
        hgoe.index(document3);
        hgoe.linkTextAndKnowledge();
        hgoe.save();
    }

    public void testSearch() throws IOException {
        HypergraphOfEntityInMemory hgoe = new HypergraphOfEntityInMemory(dbPath);

        ResultSet resultSet = hgoe.search("web search system");
        //ResultSet resultSet = hgoe.search("Monuments of India");
        //ResultSet resultSet = hgoe.search("Poirot");
        //ResultSet resultSet = hgoe.search("national park");

        for (ResultSet it = resultSet; it.hasNext(); ) {
            Result result = it.next();
            System.out.println(String.format("%.4f %s", result.getScore(), result.getNode()));
        }
    }

}
