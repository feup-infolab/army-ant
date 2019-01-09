package armyant.lucene;

import java.io.IOException;

import org.testng.annotations.Test;

@Test
public class LuceneLearningToRankHelperTest {
    private LuceneLearningToRankHelper ltrHelper;
    
    public void setUp() throws Exception {
        ltrHelper = new LuceneLearningToRankHelper("/tmp/tfr_index/lucene");
    }
    
    public void testComputeDocumentFeatures() throws Exception {
        ltrHelper.computeDocumentFeatures();
    }
}