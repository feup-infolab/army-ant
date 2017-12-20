package armyant.lucene;

import armyant.Engine;
import armyant.structures.Document;
import armyant.structures.Result;
import armyant.structures.ResultSet;
import armyant.structures.Trace;
import org.apache.lucene.analysis.Analyzer;
import org.apache.lucene.analysis.standard.StandardAnalyzer;
import org.apache.lucene.document.Field;
import org.apache.lucene.document.StringField;
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
import org.apache.lucene.search.similarities.*;
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
public class LuceneEngine extends Engine {
    private static final Logger logger = LoggerFactory.getLogger(LuceneEngine.class);

    private String path;
    private Analyzer analyzer;
    private Directory directory;
    private IndexWriter writer;

    private long counter = 0;
    private long totalTime = 0;
    private float avgTimePerDocument = 0;

    public LuceneEngine(String path) throws Exception {
        this.path = path;
        directory = FSDirectory.open(Paths.get(path));
        analyzer = new StandardAnalyzer();

        IndexWriterConfig writerConfig = new IndexWriterConfig(analyzer);
        writer = new IndexWriter(directory, writerConfig);
    }

    public void index(Document document) throws Exception {
        long startTime = System.currentTimeMillis();

        org.apache.lucene.document.Document luceneDocument = new org.apache.lucene.document.Document();
        luceneDocument.add(new StringField("doc_id", document.getDocID(), Field.Store.YES));
        luceneDocument.add(new TextField("text", document.getText(), Field.Store.YES));
        writer.addDocument(luceneDocument);

        long time = System.currentTimeMillis() - startTime;
        totalTime += time;

        counter++;
        avgTimePerDocument = counter > 1 ? (avgTimePerDocument * (counter - 1) + time) / counter : time;

        if (counter % 100 == 0) {
            logger.info(
                    "{} indexed documents in {} ({}/doc, {} docs/h)",
                    counter, formatMillis(totalTime), formatMillis(avgTimePerDocument),
                    counter * 3600000 / totalTime);
        }
    }

    public void indexCorpus(Collection<Document> corpus) {
        corpus.parallelStream().forEach(document -> {
            try {
                index(document);
            } catch (Exception e) {
                logger.warn("Error indexing document {}, skpping", document.getDocID(), e);
            }
        });
    }

    @Override
    public ResultSet search(String query, int offset, int limit) throws Exception {
        return search(query, offset, limit, RankingFunction.TF_IDF);
    }

    public ResultSet search(String query, int offset, int limit, RankingFunction rankingFunction)
            throws IOException, ParseException {
        IndexReader reader = DirectoryReader.open(directory);
        IndexSearcher searcher = new IndexSearcher(reader);

        switch (rankingFunction) {
            case TF_IDF:
                searcher.setSimilarity(new ClassicSimilarity());
                break;
            case BM25:
                searcher.setSimilarity(new BM25Similarity());
                break;
            case DFR_BE_L_H1:
                searcher.setSimilarity(new DFRSimilarity(new BasicModelBE(), new AfterEffectL(), new NormalizationH1()));
                break;
            default:
                searcher.setSimilarity(new ClassicSimilarity());
        }

        QueryParser parser = new QueryParser("text", analyzer);
        Query luceneQuery = parser.parse(query);
        ScoreDoc[] hits = searcher.search(luceneQuery, offset + limit).scoreDocs;

        ResultSet results = new ResultSet();
        results.setNumDocs((long) hits.length);
        results.setTrace(new Trace());

        int end = Math.min(offset + limit, hits.length);
        for (int i = offset; i < end; i++) {
            String docID = searcher.doc(hits[i].doc).get("doc_id");
            results.addResult(new Result(hits[i].score, null, docID));
        }

        reader.close();

        return results;
    }

    public void close() throws Exception {
        if (writer != null) writer.close();
    }

    public enum RankingFunction {
        TF_IDF,
        BM25,
        DFR_BE_L_H1
    }
}
