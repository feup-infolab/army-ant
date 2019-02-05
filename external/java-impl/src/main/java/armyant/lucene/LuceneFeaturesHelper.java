package armyant.lucene;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;

import org.apache.commons.collections4.ListUtils;
import org.apache.lucene.document.Document;
import org.apache.lucene.document.FeatureField;
import org.apache.lucene.document.StoredField;
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
    public void setDocumentFeatures(Map<String, Map<String, Float>> docFeatures) throws Exception {
        IndexReader reader = DirectoryReader.open(directory);
        IndexSearcher searcher = new IndexSearcher(reader);
        open();

        List<List<String>> batches = ListUtils.partition(new ArrayList<String>(docFeatures.keySet()), 1000);
        logger.info("Split into {} batches of 1000 documents", batches.size());

        for (List<String> batch : batches) {
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

                for (Map.Entry<String, Float> entry : docFeatures.get(docID).entrySet()) {
                    doc.add(new FeatureField("features", entry.getKey(), entry.getValue()));
                }

                writer.updateDocument(new Term("doc_id", docID), doc);
            }
        }

        close();
        reader.close();
    }
}