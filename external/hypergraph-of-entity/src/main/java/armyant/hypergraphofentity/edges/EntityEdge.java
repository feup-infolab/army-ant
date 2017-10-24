package armyant.hypergraphofentity.edges;

/**
 * Created by jldevezas on 2017-10-24.
 */
public class EntityEdge extends Edge {
    private String docID;

    public EntityEdge() {
        this.docID = null;
    }

    public EntityEdge(String docID) {
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
        return "TermEdge{" +
               "docID='" + docID + '\'' +
               '}';
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;

        EntityEdge that = (EntityEdge) o;

        return docID.equals(that.docID);
    }

    @Override
    public int hashCode() {
        return docID.hashCode();
    }
}
