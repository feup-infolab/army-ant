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
import java.util.Collection;

/**
 * Created by jldevezas on 2017-12-19.
 */
public class LuceneEngine {
    private static final Logger logger = LoggerFactory.getLogger(LuceneEngine.class);

    private String path;
    private Analyzer analyzer;
    private Directory directory;
    private IndexWriter writer;

    public LuceneEngine(String path) throws IOException {
        this.path = path;
        directory = FSDirectory.open(Paths.get(path));
        analyzer = new StandardAnalyzer();

        IndexWriterConfig writerConfig = new IndexWriterConfig(analyzer);
        writer = new IndexWriter(directory, writerConfig);
    }

    public void indexDocument(Document document) throws IOException {
        org.apache.lucene.document.Document luceneDocument = new org.apache.lucene.document.Document();
        luceneDocument.add(new TextField("text", document.getText(), TextField.Store.YES));
        writer.addDocument(luceneDocument);
    }

    public void indexCorpus(Collection<Document> corpus) {
        corpus.parallelStream().forEach(document -> {
            try {
                indexDocument(document);
            } catch (IOException e) {
                logger.warn("Error indexing document {}, skpping", document.getDocID(), e);
            }
        });
    }

    public ResultSet search(String query, int offset, int limit) throws IOException, ParseException {
        return search(query, offset, limit, RankingFunction.TF_IDF);
    }

    // TODO implement rankingFunction selection
    public ResultSet search(String query, int offset, int limit, RankingFunction rankingFunction)
            throws IOException, ParseException {
        IndexReader reader = DirectoryReader.open(directory);
        IndexSearcher searcher = new IndexSearcher(reader);

        QueryParser parser = new QueryParser("text", analyzer);
        Query luceneQuery = parser.parse(query);
        ScoreDoc[] hits = searcher.search(luceneQuery, offset + limit).scoreDocs;

        ResultSet results = new ResultSet();
        results.setNumDocs((long) hits.length);
        results.setTrace(new Trace());

        int end = Math.min(offset + limit, hits.length);
        for (int i = offset; i < end; i++) {
            results.addResult(new Result(hits[i].score, null, Integer.toString(hits[i].doc)));
        }

        reader.close();

        return results;
    }

    public void close() throws IOException {
        if (writer != null) writer.close();
    }

    public enum RankingFunction {
        TF_IDF
    }
}
