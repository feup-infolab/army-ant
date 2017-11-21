package armyant.hgoe.inmemory.nodes;

import armyant.hgoe.inmemory.Rankable;

/**
 * Created by jldevezas on 2017-10-24.
 */
public class DocumentNode extends Node implements Rankable {
    public DocumentNode() {
    }

    public DocumentNode(String name) {
        super(name);
    }

    @Override
    public void setDocID(String docID) {
        name = docID;
    }

    @Override
    public String getDocID() {
        return name;
    }
}
