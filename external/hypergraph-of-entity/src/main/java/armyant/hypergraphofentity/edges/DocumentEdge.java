package armyant.hypergraphofentity.edges;

import org.hypergraphdb.HGHandle;

/**
 * Created by jldevezas on 2017-10-24.
 */
public class DocumentEdge extends Edge {
    private String docID;

    public DocumentEdge() {

    }

    public DocumentEdge(HGHandle... outgoingSet) {
        super(outgoingSet);
    }

    public DocumentEdge(int tailIndex, HGHandle... targets) {
        super(tailIndex, targets);
    }

    public DocumentEdge(HGHandle[] head, HGHandle[] tail) {
        super(head, tail);
    }

    public DocumentEdge(String docID, HGHandle... outgoingSet) {
        super(outgoingSet);
        this.docID = docID;
    }

    public DocumentEdge(String docID, int tailIndex, HGHandle... targets) {
        super(tailIndex, targets);
        this.docID = docID;
    }

    public DocumentEdge(String docID, HGHandle[] head, HGHandle[] tail) {
        super(head, tail);
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
