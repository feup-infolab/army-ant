package armyant.hgoe.inmemory.nodes;

import java.io.Serializable;

/**
 * Created by jldevezas on 2017-10-24.
 */
public class DocumentNode extends Node implements Serializable {
    public DocumentNode() {
        super();
    }

    public DocumentNode(String name) {
        super(name);
    }
}
