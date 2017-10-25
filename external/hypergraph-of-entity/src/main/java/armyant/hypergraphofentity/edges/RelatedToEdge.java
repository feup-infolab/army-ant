package armyant.hypergraphofentity.edges;

import org.hypergraphdb.HGHandle;

/**
 * Created by jldevezas on 2017-10-25.
 */
public class RelatedToEdge extends Edge {
    private String relation;

    public RelatedToEdge(String relation) {
        this.relation = relation;
    }

    public RelatedToEdge(HGHandle... outgoingSet) {
        this("related_to", outgoingSet);
    }

    public RelatedToEdge(String relation, HGHandle... outgoingSet) {
        super(outgoingSet);
        this.relation = relation;
    }
}
