package armyant.hgoe.edges;

import armyant.hgoe.RankableAtom;

/**
 * Created by jldevezas on 2017-10-24.
 */
public class DocumentEdge extends Edge implements RankableAtom {
    private String docID;
    private String title;

    public DocumentEdge() {
    }

    public DocumentEdge(String docID) {
        this(docID, null);
    }

    public DocumentEdge(String docID, String title) {
        super();
        this.docID = docID;
        this.title = title;
    }

    @Override
    public String getID() {
        return docID;
    }

    @Override
    public void setID(String docID) {
        this.docID = docID;
    }

    @Override
    public String getName() {
        return title;
    }

    @Override
    public void setName(String title) {
        this.title = title;
    }

    @Override
    public String toString() {
        return "DocumentEdge{" + "docID='" + docID + '\'' + "title='" + title + '\'' + '}';
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
