package armyant.lucene;

import java.nio.file.Paths;

import org.apache.commons.lang3.StringUtils;
import org.apache.lucene.analysis.standard.StandardAnalyzer;
import org.apache.lucene.document.Document;
import org.apache.lucene.document.FeatureField;
import org.apache.lucene.document.Field;
import org.apache.lucene.document.StringField;
import org.apache.lucene.index.DirectoryReader;
import org.apache.lucene.index.IndexReader;
import org.apache.lucene.index.IndexWriter;
import org.apache.lucene.index.IndexWriterConfig;
import org.apache.lucene.index.Term;
import org.apache.lucene.search.IndexSearcher;
import org.apache.lucene.search.Query;
import org.apache.lucene.search.TopDocs;
import org.apache.lucene.search.similarities.BM25Similarity;
import org.apache.lucene.store.FSDirectory;
import org.testng.annotations.Test;

public class LuceneFeaturesHelperTest {
    public void testWriteFeatureFields() throws Exception {
        IndexWriterConfig writerConfig = new IndexWriterConfig(new StandardAnalyzer());
        IndexWriter writer = new IndexWriter(FSDirectory.open(Paths.get("/tmp/lucene-index")), writerConfig);

        Document doc = new Document();

        FeatureField indegree = new FeatureField("features", "indegree", 10);
        FeatureField pagerank = new FeatureField("features", "pagerank", 0.1f);

        doc.add(new StringField("doc_id", "d1", Field.Store.YES));
        doc.add(indegree);
        doc.add(pagerank);

        writer.addDocument(doc);

        writer.close();
    }

    @Test
    public void testReadFeatureFields() throws Exception {
        IndexReader reader = DirectoryReader.open(FSDirectory.open(Paths.get("/tmp/lucene-index")));
        System.out.println(reader.totalTermFreq(new Term("features", "indegree")));
        /*Bits liveDocs = MultiFields.getLiveDocs(reader);
        for (int docID = 0; docID < reader.maxDoc(); docID++) {
            if (liveDocs != null && !liveDocs.get(docID)) continue;

            Document doc = reader.document(docID);
            System.out.println(doc.get("doc_id"));
            System.out.println(reader.getTermVectors(docID));
        }*/
        reader.close();
    }

    private float reverseSigmoid(float score, float w, float k, float a) {
        return (float) Math.pow((score / w * Math.pow(k, a)) / (1 - score / w), 1 / a);
    }

    @Test
    public void testRankByFeatureFields() throws Exception {
        IndexReader reader = DirectoryReader.open(FSDirectory.open(Paths.get("/tmp/lucene-index")));

        IndexSearcher searcher = new IndexSearcher(reader);
        searcher.setSimilarity(new BM25Similarity(1.2f, 0.75f));

        float w = 1.8f;
        float k = 1f;
        float a = 0.6f;

        Query query = FeatureField.newSigmoidQuery("features", "indegree", w, k, a);
        TopDocs hits = searcher.search(query, 5);

        for (int i = 0; i < hits.scoreDocs.length; i++) {
            Document doc = searcher.doc(hits.scoreDocs[i].doc);
            float featureValue = (float) Math
                    .pow((hits.scoreDocs[i].score / w * Math.pow(k, a)) / (1 - hits.scoreDocs[i].score / w), 1 / a);
            System.out.println(featureValue + "\t" + StringUtils.abbreviate(doc.get("title"), "...", 80));
        }

        reader.close();
    }
}