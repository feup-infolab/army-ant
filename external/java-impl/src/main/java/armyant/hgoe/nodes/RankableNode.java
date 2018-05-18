package armyant.hgoe.nodes;

/**
 * Created by jldevezas on 2017-11-21.
 */
public abstract class RankableNode extends Node {
    RankableNode() {
    }

    RankableNode(String name) {
        super(name);
    }

    abstract public void setID(String id);
    abstract public String getID();

    public String getLabel() {
        return getClass().getSimpleName();
    }
}
