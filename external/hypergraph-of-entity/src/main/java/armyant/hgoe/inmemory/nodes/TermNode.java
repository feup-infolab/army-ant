package armyant.hgoe.inmemory.nodes;

import java.io.Serializable;

/**
 * Created by jldevezas on 2017-10-24.
 */
public class TermNode extends Node implements Serializable {
    public TermNode() {
        super();
    }

    public TermNode(String name) {
        super(name);
    }
}
