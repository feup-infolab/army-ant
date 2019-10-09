package armyant.lucene;

import java.io.IOException;
import java.io.InputStream;
import java.io.Reader;
import java.io.StringReader;
import java.nio.file.Paths;
import java.util.Arrays;
import java.util.Collection;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentHashMap.KeySetView;
import java.util.stream.Collectors;

import org.apache.commons.lang.NotImplementedException;
import org.apache.lucene.document.Field;
import org.apache.lucene.document.StringField;
import org.apache.lucene.index.DirectoryReader;
import org.apache.lucene.index.IndexReader;
import org.apache.lucene.index.Term;
import org.apache.lucene.queries.mlt.MoreLikeThis;
import org.apache.lucene.queryparser.classic.QueryParser;
import org.apache.lucene.search.IndexSearcher;
import org.apache.lucene.search.Query;
import org.apache.lucene.search.TermQuery;
import org.apache.lucene.search.TopDocs;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import armyant.Engine;
import armyant.structures.Document;
import armyant.structures.Entity;
import armyant.structures.Result;
import armyant.structures.ResultSet;
import armyant.structures.Trace;
import armyant.util.TextRank;
import opennlp.tools.sentdetect.SentenceDetectorME;
import opennlp.tools.sentdetect.SentenceModel;

public class LuceneEntitiesEngine extends LuceneEngine {
    private static final Logger logger = LoggerFactory.getLogger(LuceneEntitiesEngine.class);

    protected String docIndexPath;
    protected String entityIndexPath;
    protected boolean docIndexExists;
    protected LuceneEngine entityProfileEngine;
    protected KeySetView<Entity, ?> entitySet;
    protected SentenceDetectorME sentenceDetector;

    protected long entityCounter = 0;
    protected long entityTotalTime = 0;
    protected float avgTimePerEntity = 0;

    protected long collectDocumentCounter = 0;
    protected long collectEntityCounter = 0;
    protected long collectDocumentTotalTime = 0;
    protected long collectAvgTimePerDocument = 0;

    public LuceneEntitiesEngine(String path) throws Exception {
        super(Paths.get(path, "docidx").toString());

        InputStream modelIn = getClass().getResourceAsStream("/opennlp/en-sent.bin");
        SentenceModel model = new SentenceModel(modelIn);
        this.sentenceDetector = new SentenceDetectorME(model);

        this.entitySet = ConcurrentHashMap.newKeySet();

        this.docIndexPath = Paths.get(path, "docidx").toString();
        this.entityIndexPath = Paths.get(path, "entidx").toString();

        this.docIndexExists = this.indexExists;

        this.entityProfileEngine = new LuceneEngine(this.entityIndexPath);
    }

    @Override
    public void open() throws Exception {
        super.open();
        this.entityProfileEngine.open();
    }

    @Override
    public void close() throws Exception {
        this.entityProfileEngine.close();
        super.close();
    }

    public void collectEntities(Collection<Document> corpus) {
        corpus.parallelStream().forEach(document -> {
            long startTime = System.currentTimeMillis();

            try {
                for (Entity entity : document.getEntities()) {
                    entitySet.add(entity);
                    collectEntityCounter++;
                }
            } catch (Exception e) {
                logger.warn("Error indexing entities for document {}, skpping", document.getDocID(), e);
            }

            synchronized(this) {
                long time = System.currentTimeMillis() - startTime;
                collectDocumentTotalTime += time;

                collectDocumentCounter++;
                collectAvgTimePerDocument = collectDocumentCounter > 1 ?
                    (collectAvgTimePerDocument * (collectDocumentCounter - 1) + time) / collectDocumentCounter : time;

                if (collectDocumentCounter % 1000 == 0) {
                    logger.info("{} documents processed: {} collected entities ({} unique) in {} ({}/doc, {} docs/h)",
                            collectDocumentCounter, collectEntityCounter, entitySet.size(),
                            formatMillis(collectDocumentTotalTime), formatMillis(collectAvgTimePerDocument),
                            collectDocumentCounter * 3600000 / collectDocumentTotalTime);
                }
            }
        });

        logger.info("{} documents processed: {} collected entities ({} unique) in {} ({}/doc, {} docs/h)",
                collectDocumentCounter, collectEntityCounter, entitySet.size(), formatMillis(collectDocumentTotalTime),
                formatMillis(collectAvgTimePerDocument), collectDocumentCounter * 3600000 / collectDocumentTotalTime);
    }

    public String buildEntityProfile(Entity entity) throws Exception {
        // logger.info("Building entity profile for {} ({})", entity.getLabel(), entity.getURI());

        StringBuilder entityProfile = new StringBuilder();

        String query = "\"" + entity.getLabel() + "\"";
        ResultSet mentionDocs = super.search(query, 0, 1000, LuceneEngine.RankingFunction.TF_IDF, null, null, true);

        for (Result result : mentionDocs) {
            synchronized(this.sentenceDetector) {
                for (String sentence : sentenceDetector.sentDetect(result.getText())) {
                    if (sentence.contains(entity.getLabel())) {
                        entityProfile.append(sentence).append('\n');
                    }
                }
            }
        }

        return entityProfile.toString();
    }

    public void indexEntity(Entity entity, float keywordsRatio) throws Exception {
        long startTime = System.currentTimeMillis();

        org.apache.lucene.document.Document luceneDocument = new org.apache.lucene.document.Document();

        String entityProfile = buildEntityProfile(entity);
        TextRank textRank = new TextRank(entityProfile);
        entityProfile = String.join("\n", textRank.getKeywords(keywordsRatio));

        luceneDocument.add(new StringField("uri", entity.getURI(), Field.Store.YES));
        luceneDocument.add(new StringField("label", entity.getLabel(), Field.Store.YES));
        luceneDocument.add(new Field("text", entityProfile, DEFAULT_FIELD_TYPE));

        this.entityProfileEngine.writer.addDocument(luceneDocument);

        long time = System.currentTimeMillis() - startTime;
        entityTotalTime += time;

        entityCounter++;
        avgTimePerEntity = entityCounter > 1 ? (avgTimePerEntity * (entityCounter - 1) + time) / entityCounter : time;

        if (entityCounter % 100 == 0) {
            logger.info("{} indexed entities in {} ({}/ent, {} ents/h)", entityCounter, formatMillis(entityTotalTime),
                    formatMillis(avgTimePerEntity), entityCounter * 3600000 / entityTotalTime);
        }
    }

    public void indexEntities() {
        indexEntities(0.05f);
    }

    public void indexEntities(float keywordsRatio) {
        logger.info("Building entity profiles, applying keyword extraction (ratio = {}) and indexing {} entities",
                keywordsRatio, this.entitySet.size());

        entitySet.parallelStream().forEach(entity -> {
            try {
                indexEntity(entity, keywordsRatio);
            } catch (Exception e) {
                logger.warn("Error indexing entity {} ({}), skpping", entity.getURI(), entity.getLabel());
            }
        });
    }

    public boolean docIndexExists() {
        return this.docIndexExists;
    }

    public String getDocIndexPath() {
        return this.docIndexPath;
    }

    public String getEntityIndexPath() {
        return this.entityIndexPath;
    }

    public ResultSet entityRanking(String query, int offset, int limit, RankingFunction rankingFunction,
            Map<String, String> params) throws Exception {
        IndexReader reader = DirectoryReader.open(this.entityProfileEngine.directory);
        IndexSearcher searcher = new IndexSearcher(reader);
        searcher.setSimilarity(LuceneEngine.getSimilarity(rankingFunction, params));

        QueryParser parser = new QueryParser("text", analyzer);
        Query luceneQuery = parser.parse(query);

        TopDocs hits = searcher.search(luceneQuery, offset + limit);

        ResultSet results = new ResultSet();
        results.setNumDocs((long) hits.totalHits);
        results.setTrace(new Trace());

        int end = Math.min(offset + limit, hits.scoreDocs.length);
        for (int i = offset; i < end; i++) {
            org.apache.lucene.document.Document doc = searcher.doc(hits.scoreDocs[i].doc);
            String entityID = doc.get("uri");
            String label = doc.get("label");
            Result result = new Result(hits.scoreDocs[i].score, entityID, label);
            results.addResult(result);
        }

        reader.close();

        return results;
    }

    public Query buildListQuery(Set<String> entityLabels, IndexReader indexReader, IndexSearcher indexSearcher)
            throws IOException {
        StringBuilder query = new StringBuilder();

        for (String entityLabel : entityLabels) {
            Query luceneEntityQuery = new TermQuery(new Term("label", entityLabel));

            TopDocs hits = indexSearcher.search(luceneEntityQuery, 1);

            if (hits.scoreDocs.length > 0) {
                org.apache.lucene.document.Document doc = indexSearcher.doc(hits.scoreDocs[0].doc);
                query.append(doc.get("text")).append("\n\n");
            }
        }

        MoreLikeThis moreLikeThis = new MoreLikeThis(indexReader);
        moreLikeThis.setMinTermFreq(1);
        moreLikeThis.setMinDocFreq(1);
        moreLikeThis.setAnalyzer(analyzer);

        Reader reader = new StringReader(query.toString());
        return moreLikeThis.like("text", reader);
    }

    public ResultSet entityListCompletion(Set<String> entityLabels, int offset, int limit,
            RankingFunction rankingFunction, Map<String, String> params) throws Exception {
        IndexReader reader = DirectoryReader.open(this.entityProfileEngine.directory);
        IndexSearcher searcher = new IndexSearcher(reader);
        searcher.setSimilarity(getSimilarity(rankingFunction, params));

        Query luceneQuery = buildListQuery(entityLabels, reader, searcher);

        TopDocs hits = searcher.search(luceneQuery, offset + limit);

        ResultSet results = new ResultSet();
        results.setNumDocs((long) hits.totalHits);
        results.setTrace(new Trace());

        int end = Math.min(offset + limit, hits.scoreDocs.length);
        for (int i = offset; i < end; i++) {
            org.apache.lucene.document.Document doc = searcher.doc(hits.scoreDocs[i].doc);
            String entityID = doc.get("uri");
            String label = doc.get("label");
            Result result = new Result(hits.scoreDocs[i].score, entityID, label);
            results.addResult(result);
        }

        reader.close();

        return results;
    }

    @Override
    public ResultSet search(String query, int offset, int limit) throws Exception {
        throw new NotImplementedException("This overloading of search() is not supported by lucene_entities engine");
    }

    @Override
    public ResultSet search(String query, int offset, int limit, RankingFunction rankingFunction,
            Map<String, String> params) throws Exception {
        throw new NotImplementedException("This overloading of search() is not supported by lucene_entities engine");
    }

    @Override
    protected ResultSet search(String query, int offset, int limit, RankingFunction rankingFunction,
                            Map<String, String> params, Query boost, boolean includeText) throws Exception {
        throw new NotImplementedException("This overloading of search() is not supported by lucene_entities engine");
    }

    public ResultSet search(String query, int offset, int limit, Engine.QueryType queryType,
            RankingFunction rankingFunction, Map<String, String> params) throws Exception {
        long start = System.currentTimeMillis();

        if (queryType == Engine.QueryType.ENTITY_QUERY) {
            logger.info("Query type: entity query (using entity list completion)");

            Set<String> entityLabels = Arrays.stream(query.split("\\|\\|"))
                .map(String::trim)
                .collect(Collectors.toSet());

            ResultSet resultSet = entityListCompletion(entityLabels, offset, limit, rankingFunction, params);

            long end = System.currentTimeMillis();
            logger.info("{} results retrieved for [ {} ] in {}ms", resultSet.getNumDocs(), query, end - start);

            return resultSet;
        } else {
            logger.info("Query type: keyword query (using entity ranking)");

            ResultSet resultSet = entityRanking(query, offset, limit, rankingFunction, params);

            long end = System.currentTimeMillis();
            logger.info("{} results retrieved for [ {} ] in {}ms", resultSet.getNumDocs(), query, end - start);

            return resultSet;
        }
    }
}