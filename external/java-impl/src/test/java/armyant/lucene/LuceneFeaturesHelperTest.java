package armyant.lucene;

import java.nio.file.Paths;

import org.apache.lucene.analysis.standard.StandardAnalyzer;
import org.apache.lucene.document.Document;
import org.apache.lucene.document.FeatureField;
import org.apache.lucene.document.Field;
import org.apache.lucene.document.StringField;
import org.apache.lucene.index.DirectoryReader;
import org.apache.lucene.index.IndexReader;
import org.apache.lucene.index.IndexWriter;
import org.apache.lucene.index.IndexWriterConfig;
import org.apache.lucene.index.MultiFields;
import org.apache.lucene.index.Term;
import org.apache.lucene.store.FSDirectory;
import org.apache.lucene.util.Bits;
import org.testng.annotations.Test;

@Test
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
    }
}