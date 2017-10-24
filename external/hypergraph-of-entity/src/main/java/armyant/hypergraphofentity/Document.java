package armyant.hypergraphofentity;

import java.util.ArrayList;
import java.util.List;

/**
 * Created by jldevezas on 2017-10-23.
 */
public class Document {
    private String docID;
    private String text;
    private List<Triple> triples;

    public Document(String docID, String text, List<Triple> triples) {
        this.docID = docID;
        this.text = text;
        this.triples = triples;
    }

    public String getDocID() {
        return docID;
    }

    public void setDocID(String docID) {
        this.docID = docID;
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
            this.triples = new ArrayList<Triple>();
        }

        this.triples.add(triple);
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;

        Document document = (Document) o;

        return docID.equals(document.docID);
    }

    @Override
    public int hashCode() {
        return docID.hashCode();
    }
}
