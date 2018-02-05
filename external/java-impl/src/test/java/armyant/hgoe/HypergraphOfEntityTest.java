package armyant.hgoe;

import armyant.structures.Document;
import armyant.structures.Triple;
import grph.path.ArrayListPath;
import grph.path.Path;
import org.testng.annotations.Test;

import java.util.Arrays;
import java.util.Collections;

/**
 * Created by jldevezas on 2017-11-29.
 */
@Test
public class HypergraphOfEntityTest {
    public static final Document document1 = new Document(
            "D1",

            "Semantic Search",

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

            "Search engine technology",

            "A search engine is an information retrieval software program that discovers, crawls, transforms and " +
            "stores information for retrieval and presentation in response to user queries.",

            Arrays.asList(
                    new Triple("Search engine technology", "related_to", "Search engine")
            )
    );

    public static final Document document3 = new Document(
            "D3",

            "Unreachable Document",

            "Unreachable people.",

            Collections.singletonList(new Triple("Unreachable Me", "related_to", "Unreachable You"))
    );

    public void testPath() {
        Path path = new ArrayListPath();
        path.extend(10);
        path.extend(1, 20);
        path.extend(2, 10);
        path.extend(3, 20);
        path.extend(30);
        System.out.println(path);
        System.out.println(path.getLength());
        System.out.println(path.indexOfVertex(10));
    }
}
