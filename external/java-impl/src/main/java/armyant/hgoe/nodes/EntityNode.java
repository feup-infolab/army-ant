package armyant.hgoe.nodes;

/**
 * Created by jldevezas on 2017-10-24.
 */
public class EntityNode extends RankableNode {
    private String entityURI;

    public EntityNode() {
    }

    public EntityNode(String entityURI, String label) {
        super(label);
        this.entityURI = entityURI;
    }

    @Override
    public void setID(String id) {
        entityURI = id;
    }

    @Override
    public String getID() {
        return entityURI;
    }
}
