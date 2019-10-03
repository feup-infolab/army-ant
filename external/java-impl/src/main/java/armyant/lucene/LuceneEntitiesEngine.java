package armyant.lucene;

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.file.Paths;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collection;
import java.util.Collections;
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

    protected float avgTimePerEntity = 0;
    protected String entityIndexPath;
    protected boolean entityProfileIndexExisted;
    protected LuceneEngine entityProfileEngine;
    protected KeySetView<Entity, ?> entitySet;

    public LuceneEntitiesEngine(String path) throws Exception {
        super(Paths.get(path, "docidx").toString());

        this.entitySet = ConcurrentHashMap.newKeySet();

        this.entityIndexPath = Paths.get(path, "entidx").toString();
        this.entityProfileIndexExisted = new File(this.entityIndexPath).exists();
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
        StringBuilder entityProfile = new StringBuilder();

        try (InputStream modelIn = new FileInputStream("en-sent.bin")) {
            SentenceModel model = new SentenceModel(modelIn);
            SentenceDetectorME sentenceDetector = new SentenceDetectorME(model);

            ResultSet mentionDocs = this.entityProfileEngine.search("\"" + entity.getLabel() + "\"", 0, 1000);

            List<String> sentences = new ArrayList<>();
            for (Result result : mentionDocs) {
                System.out.println(result.getText());
                sentences.addAll(Arrays.asList(sentenceDetector.sentDetect(result.getText())));
            }

            for (String sentence : sentences) {
                if (sentence.contains(entity.getLabel())) {
                    entityProfile.append(sentence).append('\n');
                }
            }
        }

        return entityProfile.toString();
    }

    public void indexEntity(Entity entity) throws Exception {
        org.apache.lucene.document.Document luceneDocument = new org.apache.lucene.document.Document();

        String entityProfile = buildEntityProfile(entity);
        System.out.println(entity.getLabel() + ":\n" + entityProfile + "\n");
        TextRank textRank = new TextRank(entityProfile);
        entityProfile = String.join("\n", textRank.getKeywords());
        System.out.println(entity.getLabel() + " (keywords):\n" + entityProfile + "\n");

        luceneDocument.add(new StringField("uri", entity.getURI(), Field.Store.YES));
        luceneDocument.add(new Field("text", entityProfile, DEFAULT_FIELD_TYPE));

        this.entityProfileEngine.writer.addDocument(luceneDocument);
    }

    public void indexEntities() {
        if (this.entityProfileIndexExisted) {
            logger.warn(
                "Entity index already exists at '{}'', using current version (delete it to recreate)",
                this.entityIndexPath);
            return;
        }

        entitySet.parallelStream().forEach(entity -> {
            try {
                indexEntity(entity);
            } catch (Exception e) {
                logger.warn(
                    String.format("Error indexing entity %s (%s), skpping", entity.getURI(), entity.getLabel()), e);
            }
        });
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