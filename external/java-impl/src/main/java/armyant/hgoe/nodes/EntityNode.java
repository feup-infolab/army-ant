package armyant.hgoe.nodes;

import armyant.hgoe.RankableAtom;
import armyant.structures.Entity;

/**
 * Created by jldevezas on 2017-10-24.
 */
public class EntityNode extends Node implements RankableAtom {
    private String entityURI;

    public EntityNode() {
    }

    public EntityNode(Entity entity) {
        super(entity.getLabel());
        this.entityURI = entity.getURI();
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
