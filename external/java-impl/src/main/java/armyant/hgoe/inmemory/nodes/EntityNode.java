package armyant.hgoe.inmemory.nodes;

import armyant.hgoe.inmemory.Rankable;
import armyant.structures.Document;

/**
 * Created by jldevezas on 2017-10-24.
 */
public class EntityNode extends Node implements Rankable {
    private String docID;

    public EntityNode() {
    }

    public EntityNode(String name) {
        this(null, name);
    }

    public EntityNode(Document document, String name) {
        super(name);
        if (name.equals(document.getTitle())) {
            this.docID = document.getDocID();
        } else {
            this.docID = null;
        }
    }

    @Override
    public void setDocID(String docID) {
        this.docID = docID;
    }

    @Override
    public String getDocID() {
        return docID;
    }

    public boolean hasDocID() {
        return docID != null;
    }
}
