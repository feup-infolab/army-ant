package armyant.hypergraphofentity.nodes;

/**
 * Created by jldevezas on 2017-10-24.
 */
public class EntityNode extends Node {
    public EntityNode() {
    }

    public EntityNode(String name) {
        super(name);
    }

    @Override
    public String getType() {
        return "entity";
    }
}
