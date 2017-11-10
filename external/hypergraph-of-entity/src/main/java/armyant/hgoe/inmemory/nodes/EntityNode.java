package armyant.hgoe.inmemory.nodes;

import java.io.Serializable;

/**
 * Created by jldevezas on 2017-10-24.
 */
public class EntityNode extends Node implements Serializable {
    public EntityNode() {
        super();
    }

    public EntityNode(String name) {
        super(name);
    }
}
