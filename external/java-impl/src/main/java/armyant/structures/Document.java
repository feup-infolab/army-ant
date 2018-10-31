package armyant.structures;

import java.util.ArrayList;
import java.util.List;

/**
 * Created by jldevezas on 2017-10-23.
 */
public class Document {
    private Double score;
    private String docID;
    private String title;
    private String text;
    private List<Entity> entities;
    private List<Triple> triples;

    public Document(String docID, String title, String text, List<Triple> triples) {
        this(null, docID, title, text, triples, null);
    }

    public Document(String docID, String title, String text, List<Triple> triples, List<Entity> entities) {
        this(null, docID, title, text, triples, entities);
    }

    public Document(Double score, String docID, String title, String text, List<Triple> triples) {
        this(score, docID, title, text, triples, null);
    }

    public Document(Double score, String docID, String title, String text, List<Triple> triples, List<Entity> entities) {
        this.score = score;
        this.docID = docID;
        this.title = title;
        this.text = text;
        this.entities = entities;
        this.triples = triples;
    }

    public Double getScore() {
        return score;
    }

    public void setScore(Double score) {
        this.score = score;
    }

    public String getDocID() {
        return docID;
    }

    public void setDocID(String docID) {
        this.docID = docID;
    }

    public String getTitle() {
        return title;
    }

    public void setTitle(String title) {
        this.title = title;
    }

    public String getText() {
        return text;
    }

    public void setText(String text) {
        this.text = text;
    }

    public List<Triple> getTriples() {
        return triples;
    }

    public void setTriples(List<Triple> triples) {
        this.triples = triples;
    }

    public void addTriple(Triple triple) {
        if (this.triples == null) {
            this.triples = new ArrayList<>();
        }

        this.triples.add(triple);
    }

    public List<Entity> getEntities() {
        return entities;
    }

    public void setEntities(List<Entity> entities) {
        this.entities = entities;
    }

    public void addEntity(Entity entity) {
        if (this.entities == null) {
            this.entities = new ArrayList<>();
        }

        this.entities.add(entity);
    }

    public boolean hasEntities() {
        return this.entities != null && this.entities.size() > 0;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o)
            return true;
        if (o == null || getClass() != o.getClass())
            return false;

        Document document = (Document) o;

        return docID.equals(document.docID);
    }

    @Override
    public int hashCode() {
        return docID.hashCode();
    }

    @Override
    public String toString() {
        return "Document{" + (score != null ? "score=" + score : "") + ", docID='" + docID + '\'' + '}';
    }
}
