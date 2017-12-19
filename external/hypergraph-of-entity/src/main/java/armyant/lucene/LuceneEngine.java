package armyant.lucene;

import armyant.structures.Document;
import armyant.structures.Result;
import armyant.structures.ResultSet;
import armyant.structures.Trace;
import org.apache.lucene.analysis.Analyzer;
import org.apache.lucene.analysis.standard.StandardAnalyzer;
import org.apache.lucene.document.TextField;
import org.apache.lucene.index.DirectoryReader;
import org.apache.lucene.index.IndexReader;
import org.apache.lucene.index.IndexWriter;
import org.apache.lucene.index.IndexWriterConfig;
import org.apache.lucene.queryparser.classic.ParseException;
import org.apache.lucene.queryparser.classic.QueryParser;
import org.apache.lucene.search.IndexSearcher;
import org.apache.lucene.search.Query;
import org.apache.lucene.search.ScoreDoc;
import org.apache.lucene.store.Directory;
import org.apache.lucene.store.FSDirectory;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.nio.file.Paths;
import java.util.Arrays;

/**
 * Created by jldevezas on 2017-12-19.
 */
public class LuceneEngine {
    private static final Logger logger = LoggerFactory.getLogger(LuceneEngine.class);

    private String path;
    private Analyzer lAnalyzer;
    private IndexWriter lWriter = null;

    public LuceneEngine(String path) {
        try {
            this.path = path;
            lAnalyzer = new StandardAnalyzer();

            Directory lDirectory = FSDirectory.open(Paths.get(path));
            IndexWriterConfig lWriterConfig = new IndexWriterConfig(lAnalyzer);
            lWriter = new IndexWriter(lDirectory, lWriterConfig);
        } catch (IOException e) {
            logger.error(e.getMessage(), e);
        }
    }

    public void indexDocument(Document document) {
        if (lWriter == null) {
            logger.error("Index writer is null");
            return;
        }

        try {
            org.apache.lucene.document.Document lDoc = new org.apache.lucene.document.Document();
            lDoc.add(new TextField("text", document.getText(), TextField.Store.YES));
            lWriter.addDocument(lDoc);
        } catch (IOException e) {
            logger.error(e.getMessage(), e);
        }
    }

    public ResultSet search(String query, int offset, int limit) throws IOException, ParseException {
        return search(query, offset, limit, RankingFunction.TF_IDF);
    }

    // TODO implement rankingFunction selection
    public ResultSet search(String query, int offset, int limit, RankingFunction rankingFunction)
            throws IOException, ParseException {
        IndexReader lReader = DirectoryReader.open(FSDirectory.open(Paths.get(path)));
        IndexSearcher lSearcher = new IndexSearcher(lReader);

        QueryParser parser = new QueryParser("content", lAnalyzer);
        Query lQuery = parser.parse(query);
        ScoreDoc[] hits = lSearcher.search(lQuery, offset+limit).scoreDocs;
        Arrays.stream(hits).forEach(System.out::println);

        ResultSet results = new ResultSet();
        results.setNumDocs((long) hits.length);
        results.setTrace(new Trace());

        int end = Math.min(offset+limit, hits.length);
        for (int i = offset; i < end; i++) {
            results.addResult(new Result(hits[i].score, null, Integer.toString(hits[i].doc)));
        }

        lReader.close();

        return results;
    }

    public void close() {
        try {
            if (lWriter != null) lWriter.close();
        } catch (IOException e) {
            logger.error(e.getMessage(), e);
        }
    }

    public enum RankingFunction {
        TF_IDF
    }
}
