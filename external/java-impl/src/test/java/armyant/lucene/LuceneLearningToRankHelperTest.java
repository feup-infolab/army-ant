package armyant.lucene;

import java.util.ArrayList;
import java.util.List;

import org.testng.annotations.BeforeClass;
import org.testng.annotations.Test;

import armyant.structures.Result;
import armyant.structures.ResultSet;

public class LuceneLearningToRankHelperTest {
    private LuceneLearningToRankHelper ltrHelper;

    @BeforeClass
    public void setUp() throws Exception {
        ltrHelper = new LuceneLearningToRankHelper("/tmp/tfr_index/lucene");
    }

    @Test
    public void testComputeDocumentFeatures() throws Exception {
        ltrHelper.computeDocumentFeatures();
    }

    @Test
    public void testComputeQueryDocumentFeatures() throws Exception {
        String query = "great rock music";

        ResultSet results = ltrHelper.search(query, 0, 10);

        List<String> docIDs = new ArrayList<>();
        for (Result result : results) {
            docIDs.add(result.getID());
        }

        ltrHelper.computeQueryDocumentFeatures(query, docIDs);
    }
}