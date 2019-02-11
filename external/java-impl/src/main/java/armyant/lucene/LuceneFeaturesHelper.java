package armyant.lucene;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.apache.commons.collections4.ListUtils;
import org.apache.lucene.document.Document;
import org.apache.lucene.document.FeatureField;
import org.apache.lucene.index.DirectoryReader;
import org.apache.lucene.index.IndexReader;
import org.apache.lucene.index.Term;
import org.apache.lucene.search.BooleanClause;
import org.apache.lucene.search.BooleanQuery;
import org.apache.lucene.search.IndexSearcher;
import org.apache.lucene.search.Query;
import org.apache.lucene.search.ScoreDoc;
import org.apache.lucene.search.TermQuery;
import org.apache.lucene.search.TopDocs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import armyant.structures.ResultSet;

public class LuceneFeaturesHelper extends LuceneEngine {
    private static final Logger logger = LoggerFactory.getLogger(LuceneFeaturesHelper.class);

    public LuceneFeaturesHelper(String path) throws Exception {
        super(path);
    }

    /**
     * Updates/creates all in a "features" FeatureField, but only for existing documents.
     *
     * @param docFeatures
     * @throws Exception
     */
    public void setDocumentFeatures(Map<String, Map<String, Double>> docFeatures) throws Exception {
        IndexReader reader = DirectoryReader.open(directory);
        IndexSearcher searcher = new IndexSearcher(reader);
        open();

        List<List<String>> batches = ListUtils.partition(new ArrayList<String>(docFeatures.keySet()), 1000);
        logger.info("Split into {} batches of 1000 documents", batches.size());

        int batchCount = 0;
        for (List<String> batch : batches) {
            logger.info("Processing batch {}", ++batchCount);

            BooleanQuery.Builder queryBuilder = new BooleanQuery.Builder();
            for (String docID : batch) {
                queryBuilder.add(new TermQuery(new Term("doc_id", docID)), BooleanClause.Occur.SHOULD);
            }
            Query query = queryBuilder.build();

            TopDocs hits = searcher.search(query, batch.size());
            for (ScoreDoc scoreDoc : hits.scoreDocs) {
                Document doc = reader.document(scoreDoc.doc);
                String docID = doc.get("doc_id");

                if (!docFeatures.containsKey(docID)) {
                    logger.warn("Document {} not found in index, ignoring", docID);
                    continue;
                }

                if (docFeatures.get(docID).isEmpty()) {
                    logger.warn("No features for document {}, ignoring", docID);
                    continue;
                }

                doc.removeFields("features");

                for (Map.Entry<String, Double> entry : docFeatures.get(docID).entrySet()) {
                    float featureValue = entry.getValue().floatValue();
                    if (featureValue < Float.MIN_NORMAL) featureValue = Float.MIN_NORMAL;
                    doc.add(new FeatureField("features", entry.getKey(), featureValue));
                }

                writer.updateDocument(new Term("doc_id", docID), doc);
            }
        }

        close();
        reader.close();
    }

    @Override
    public ResultSet search(String query, int offset, int limit) throws Exception {
        Map<String, String> params = new HashMap<>();

        params.put("k1", "1.2");
        params.put("b", "0.75");
        params.put("feature", "pr");
        params.put("w", "1.8");
        params.put("k", "1.0");
        params.put("a", "0.6");

        return search(query, offset, limit, RankingFunction.BM25, params);
    }

    @Override
    public ResultSet search(String query, int offset, int limit, RankingFunction rankingFunction,
            Map<String, String> params) throws Exception {

        String featureName = params.get("feature");
        if (featureName != null && featureName.equals("Disabled")) featureName = null;
        float w = params.get("w") == null ? 1.8f : Float.parseFloat(params.get("w"));
        float k = params.get("k") == null ? 1.0f : Float.parseFloat(params.get("k"));
        float a = params.get("a") == null ? 0.6f : Float.parseFloat(params.get("a"));

        params.remove("feature");
        params.remove("w");
        params.remove("k");
        params.remove("a");

        Query boost = featureName == null ? null : FeatureField.newSigmoidQuery("features", featureName, w, k, a);
        return search(query, offset, limit, rankingFunction, params, boost);
    }
}