package armyant.hgoe.inmemory.edges;

import armyant.hgoe.inmemory.Rankable;

/**
 * Created by jldevezas on 2017-10-24.
 */
public class DocumentEdge extends Edge implements Rankable {
    private String docID;

    public DocumentEdge() {
    }

    public DocumentEdge(String docID) {
        super();
        this.docID = docID;
    }

    public String getDocID() {
        return docID;
    }

    public void setDocID(String docID) {
        this.docID = docID;
    }

    @Override
    public String toString() {
        return "DocumentEdge{" +
               "docID='" + docID + '\'' +
               '}';
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;

        DocumentEdge that = (DocumentEdge) o;

        return docID.equals(that.docID);
    }

    @Override
    public int hashCode() {
        return docID.hashCode();
    }
}
