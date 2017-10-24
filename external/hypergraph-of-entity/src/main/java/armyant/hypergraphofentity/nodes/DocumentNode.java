package armyant.hypergraphofentity.nodes;

/**
 * Created by jldevezas on 2017-10-24.
 */
public class DocumentNode extends Node {
    public DocumentNode() {
    }

    public DocumentNode(String name) {
        super(name);
    }

    @Override
    public String getType() {
        return "document";
    }
}
