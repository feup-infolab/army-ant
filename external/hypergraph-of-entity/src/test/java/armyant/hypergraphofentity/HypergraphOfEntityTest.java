package armyant.hypergraphofentity;

import org.testng.annotations.Test;

import java.io.IOException;
import java.util.Arrays;

/**
 * Created by jldevezas on 2017-10-23.
 */
@Test
public class HypergraphOfEntityTest {

    public static final Document document1 = new Document(
            "D1",

            "Semantic search seeks to improve search accuracy by understanding the searcher's intent and the " +
            "contextual meaning of terms as they appear in the searchable dataspace, whether on the Web or within a " +
            "closed system, to generate more relevant results.",

            Arrays.asList(
                    Triple.create("Semantic search", "related_to", "Search engine technology"),
                    Triple.create("Semantic search", "related_to", "Intention"),
                    Triple.create("Semantic search", "related_to", "Context (language use)"),
                    Triple.create("Semantic search", "related_to", "World Wide Web")
            )
    );

    public static final Document document2 = new Document(
            "D2",

            "A search engine is an information retrieval software program that discovers, crawls, transforms and " +
            "stores information for retrieval and presentation in response to user queries.",

            Arrays.asList(
                    Triple.create("Search engine technology", "related_to", "Search engine")
            )
    );

    public void testIndex() throws IOException {
        HypergraphOfEntity hgoe = new HypergraphOfEntity("/tmp/hgoe.db");
        hgoe.index(document1);
        hgoe.index(document2);
        hgoe.printNodes();
        hgoe.close();
    }

    public void testSearch() throws IOException {
        HypergraphOfEntity hgoe = new HypergraphOfEntity("/tmp/hgoe.db");
        //hgoe.printDepthFirst("web");
        hgoe.search("web search system nomatchforme");
        hgoe.close();
    }

}
