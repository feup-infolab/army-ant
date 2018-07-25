package armyant.hgoe.nodes;

import armyant.hgoe.RankableAtom;

/**
 * Created by jldevezas on 2017-10-24.
 */
public class EntityNode extends Node implements RankableAtom {
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
