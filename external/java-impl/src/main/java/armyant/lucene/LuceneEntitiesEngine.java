package armyant.lucene;

import java.io.InputStream;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentHashMap.KeySetView;

import org.apache.lucene.document.Field;
import org.apache.lucene.document.StringField;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import armyant.Engine;
import armyant.structures.Document;
import armyant.structures.Entity;
import armyant.structures.Result;
import armyant.structures.ResultSet;
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

    protected long entityCounter = 0;
    protected long entityTotalTime = 0;
    protected float avgTimePerEntity = 0;

    public LuceneEntitiesEngine(String path) throws Exception {
        super(Paths.get(path, "docidx").toString());

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
            try {
                for (Entity entity : document.getEntities()) {
                    entitySet.add(entity);
                }
            } catch (Exception e) {
                logger.warn("Error indexing entities for document {}, skpping", document.getDocID(), e);
            }
        });
    }

    public String buildEntityProfile(Entity entity) throws Exception {
        //logger.info("Building entity profile for {} ({})", entity.getLabel(), entity.getURI());

        StringBuilder entityProfile = new StringBuilder();

        InputStream modelIn = getClass().getResourceAsStream("/opennlp/en-sent.bin");
        SentenceModel model = new SentenceModel(modelIn);
        SentenceDetectorME sentenceDetector = new SentenceDetectorME(model);

        ResultSet mentionDocs = this.search(
            "\"" + entity.getLabel() + "\"", 0, 1000, LuceneEngine.RankingFunction.TF_IDF, null, null, true);

        List<String> sentences = new ArrayList<>();
        for (Result result : mentionDocs) {
            sentences.addAll(Arrays.asList(sentenceDetector.sentDetect(result.getText())));
        }

        for (String sentence : sentences) {
            if (sentence.contains(entity.getLabel())) {
                entityProfile.append(sentence).append('\n');
            }
        }

        return entityProfile.toString();
    }

    public void indexEntity(Entity entity) throws Exception {
        long startTime = System.currentTimeMillis();

        org.apache.lucene.document.Document luceneDocument = new org.apache.lucene.document.Document();

        String entityProfile = buildEntityProfile(entity);
        TextRank textRank = new TextRank(entityProfile);
        entityProfile = String.join("\n", textRank.getKeywords());

        luceneDocument.add(new StringField("uri", entity.getURI(), Field.Store.YES));
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
        logger.info(
            "Building entity profiles, applying keyword extraction and indexing {} entities",
            this.entitySet.size());

        entitySet.parallelStream().forEach(entity -> {
            try {
                indexEntity(entity);
            } catch (Exception e) {
                logger.warn(
                    String.format("Error indexing entity %s (%s), skpping", entity.getURI(), entity.getLabel()), e);
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

    public ResultSet search(String query, int offset, int limit, Engine.QueryType queryType, Engine.Task task,
            RankingFunction function, Map<String, String> params, boolean debug) {
        long start = System.currentTimeMillis();

        ResultSet resultSet = new ResultSet();

        long end = System.currentTimeMillis();

        logger.info("{} results retrieved for [ {} ] in {}ms", resultSet.getNumDocs(), query, end - start);

        return null;
    }
}