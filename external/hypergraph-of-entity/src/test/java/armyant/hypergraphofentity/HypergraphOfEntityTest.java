package armyant.hypergraphofentity;

import org.testng.annotations.Test;

import java.io.IOException;
import java.util.Arrays;

/**
 * Created by jldevezas on 2017-10-23.
 */
@Test
public class HypergraphOfEntityTest {

    public static final Document document = Document.create(
            "d1",
            "Semantic search seeks to improve search accuracy by understanding the searcher's intent and the contextual meaning of terms as they appear in the searchable dataspace, whether on the Web or within a closed system, to generate more relevant results.",
            Arrays.asList(
                    Triple.create("Semantic search", "related_to", "Search engine technology"),
                    Triple.create("Semantic search", "related_to", "Intention"),
                    Triple.create("Semantic search", "related_to", "Context (language use)"),
                    Triple.create("Semantic search", "related_to", "World Wide Web")
            )
    );

    public void testIndex() throws IOException {
        HypergraphOfEntity hgoe = new HypergraphOfEntity("/tmp/hgoe.db");
        hgoe.indexDocument(document);
    }

}
