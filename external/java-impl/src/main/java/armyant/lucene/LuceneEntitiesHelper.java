package armyant.lucene;

import java.io.File;
import java.io.IOException;
import java.nio.file.Paths;
import java.util.Collection;
import java.util.Collections;
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
import armyant.structures.ResultSet;

public class LuceneEntitiesHelper extends LuceneEngine {
    private static final Logger logger = LoggerFactory.getLogger(LuceneEntitiesHelper.class);

    protected float avgTimePerEntity = 0;
    protected String entityIndexPath;
    protected LuceneEngine entityProfileEngine;
    protected KeySetView<Entity, ?> entitySet;

    public LuceneEntitiesHelper(String path) throws Exception {
        super(Paths.get(path, "docidx").toString());

        this.entitySet = ConcurrentHashMap.newKeySet();

        this.entityIndexPath = Paths.get(path, "entidx").toString();
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

    public String buildEntityProfile(Entity entity) {
        StringBuilder entityProfile = new StringBuilder();

        // TODO fetch documents mentioning entity, split into sentences and filter sentences mentioning entity

        return entityProfile.toString();
    }

    public void indexEntity(Entity entity) throws IOException {
        org.apache.lucene.document.Document luceneDocument = new org.apache.lucene.document.Document();

        luceneDocument.add(new StringField("uri", entity.getURI(), Field.Store.YES));
        luceneDocument.add(new Field("text", buildEntityProfile(entity), DEFAULT_FIELD_TYPE));

        this.entityProfileEngine.writer.addDocument(luceneDocument);
    }

    public void indexEntities() {
        entitySet.parallelStream().forEach(entity -> {
            try {
                indexEntity(entity);
            } catch (IOException e) {
                logger.warn("Error indexing entity {} ({}), skpping", entity.getURI(), entity.getLabel(), e);
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