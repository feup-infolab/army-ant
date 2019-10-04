package armyant.lucene;

import java.io.File;
import java.nio.file.Paths;
import java.util.Collection;
import java.util.Map;

import org.apache.lucene.analysis.Analyzer;
import org.apache.lucene.analysis.standard.StandardAnalyzer;
import org.apache.lucene.document.Field;
import org.apache.lucene.document.FieldType;
import org.apache.lucene.document.StringField;
import org.apache.lucene.index.DirectoryReader;
import org.apache.lucene.index.IndexOptions;
import org.apache.lucene.index.IndexReader;
import org.apache.lucene.index.IndexWriter;
import org.apache.lucene.index.IndexWriterConfig;
import org.apache.lucene.queryparser.classic.QueryParser;
import org.apache.lucene.search.BooleanClause.Occur;
import org.apache.lucene.search.BooleanQuery;
import org.apache.lucene.search.IndexSearcher;
import org.apache.lucene.search.Query;
import org.apache.lucene.search.TopDocs;
import org.apache.lucene.search.similarities.AfterEffect;
import org.apache.lucene.search.similarities.BM25Similarity;
import org.apache.lucene.search.similarities.BasicModel;
import org.apache.lucene.search.similarities.ClassicSimilarity;
import org.apache.lucene.search.similarities.DFRSimilarity;
import org.apache.lucene.search.similarities.Normalization;
import org.apache.lucene.store.Directory;
import org.apache.lucene.store.FSDirectory;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import armyant.Engine;
import armyant.structures.Document;
import armyant.structures.Result;
import armyant.structures.ResultSet;
import armyant.structures.Trace;

/**
 * Created by jldevezas on 2017-12-19.
 */
public class LuceneEngine extends Engine {
    private static final Logger logger = LoggerFactory.getLogger(LuceneEngine.class);

    public static FieldType DEFAULT_FIELD_TYPE;

    static {
        DEFAULT_FIELD_TYPE = new FieldType();
        DEFAULT_FIELD_TYPE.setIndexOptions(IndexOptions.DOCS_AND_FREQS_AND_POSITIONS);
        DEFAULT_FIELD_TYPE.setTokenized(true);
        DEFAULT_FIELD_TYPE.setStored(true);
        DEFAULT_FIELD_TYPE.setStoreTermVectors(true);
        DEFAULT_FIELD_TYPE.setStoreTermVectorPositions(true);
        DEFAULT_FIELD_TYPE.freeze();
    }

    protected String path;
    protected Analyzer analyzer;
    protected Directory directory;
    protected IndexWriter writer;
    protected boolean indexExists;

    protected long counter = 0;
    protected long totalTime = 0;
    protected float avgTimePerDocument = 0;

    public LuceneEngine(String path) throws Exception {
        this.path = path;
        indexExists = new File(path).exists();
        directory = FSDirectory.open(Paths.get(path));
        analyzer = new StandardAnalyzer();
    }

    public void open() throws Exception {
        logger.info("Opening {} for indexing", this.path);
        IndexWriterConfig writerConfig = new IndexWriterConfig(analyzer);
        writer = new IndexWriter(directory, writerConfig);
    }

    public void index(Document document) throws Exception {
        long startTime = System.currentTimeMillis();

        org.apache.lucene.document.Document luceneDocument = new org.apache.lucene.document.Document();
        luceneDocument.add(new StringField("doc_id", document.getDocID(), Field.Store.YES));
        if (document.getTitle() != null) {
            luceneDocument.add(new Field("title", document.getTitle(), DEFAULT_FIELD_TYPE));
        }
        luceneDocument.add(new Field("text", document.getText(), DEFAULT_FIELD_TYPE));
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

    public static void setSimilarity(IndexSearcher searcher, RankingFunction rankingFunction,
            Map<String, String> params) throws Exception {
        switch (rankingFunction) {
        case TF_IDF:
            searcher.setSimilarity(new ClassicSimilarity());
            break;
        case BM25:
            searcher.setSimilarity(
                    new BM25Similarity(Float.parseFloat(params.get("k1")), Float.parseFloat(params.get("b"))));
            break;
        case DFR:
            BasicModel basicModel = (BasicModel) Class
                    .forName("org.apache.lucene.search.similarities.BasicModel" + params.get("BM")).newInstance();

            AfterEffect afterEffect;
            if (params.get("AE").equals("Disabled")) {
                afterEffect = new AfterEffect.NoAfterEffect();
            } else {
                afterEffect = (AfterEffect) Class
                        .forName("org.apache.lucene.search.similarities.AfterEffect" + params.get("AE")).newInstance();
            }

            Normalization normalization;
            if (params.get("N").equals("Disabled")) {
                normalization = new Normalization.NoNormalization();
            } else {
                normalization = (Normalization) Class
                        .forName("org.apache.lucene.search.similarities.Normalization" + params.get("N")).newInstance();
            }

            searcher.setSimilarity(new DFRSimilarity(basicModel, afterEffect, normalization));
            break;
        default:
            searcher.setSimilarity(new ClassicSimilarity());
        }
    }

    @Override
    public ResultSet search(String query, int offset, int limit) throws Exception {
        return search(query, offset, limit, RankingFunction.TF_IDF, null);
    }

    public ResultSet search(String query, int offset, int limit, RankingFunction rankingFunction,
                            Map<String, String> params) throws Exception {
        return search(query, offset, limit, rankingFunction, params, null, false);
    }

    protected ResultSet search(String query, int offset, int limit, RankingFunction rankingFunction,
                            Map<String, String> params, Query boost, boolean includeText) throws Exception {
        IndexReader reader = DirectoryReader.open(directory);
        IndexSearcher searcher = new IndexSearcher(reader);
        setSimilarity(searcher, rankingFunction, params);

        QueryParser parser = new QueryParser("text", analyzer);
        Query luceneQuery = parser.parse(query);

        if (boost != null) {
            logger.info("Using query boosting");
            luceneQuery = new BooleanQuery.Builder()
                .add(luceneQuery, Occur.MUST)
                .add(boost, Occur.SHOULD)
                .build();
        }

        TopDocs hits = searcher.search(luceneQuery, offset + limit);

        ResultSet results = new ResultSet();
        results.setNumDocs((long) hits.totalHits);
        results.setTrace(new Trace());

        int end = Math.min(offset + limit, hits.scoreDocs.length);
        for (int i = offset; i < end; i++) {
            org.apache.lucene.document.Document doc = searcher.doc(hits.scoreDocs[i].doc);
            String docID = doc.get("doc_id");
            String title = doc.get("title");
            Result result = new Result(hits.scoreDocs[i].score, docID, title);
            if (includeText) {
                String text = doc.get("text");
                result.setText(text);
            }
            results.addResult(result);
        }

        reader.close();

        return results;
    }

    public void close() throws Exception {
        logger.info("Closing index writer");
        if (writer != null) writer.close();
    }

    public enum RankingFunction {
        TF_IDF,
        BM25,
        DFR
    }
}