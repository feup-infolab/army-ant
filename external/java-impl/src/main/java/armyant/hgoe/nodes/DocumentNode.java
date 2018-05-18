package armyant.hgoe.nodes;

/**
 * Created by jldevezas on 2017-10-24.
 */
public class DocumentNode extends RankableNode {
    private String docID;

    public DocumentNode() {
    }

    public DocumentNode(String docID, String title) {
        super(title);
        this.docID = docID;
    }

    @Override
    public void setID(String id) {
        docID = id;
    }

    @Override
    public String getID() {
        return docID;
    }
}
