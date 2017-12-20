package armyant.hgoe.indisk.edges;

import org.hypergraphdb.HGHandle;

/**
 * Created by jldevezas on 2017-10-25.
 */
public class RelatedToEdge extends Edge {
    private String relation;

    public RelatedToEdge() {

    }


    public RelatedToEdge(HGHandle... outgoingSet) {
        this("related_to", outgoingSet);
    }

    public RelatedToEdge(String relation, HGHandle... outgoingSet) {
        super(outgoingSet);
        this.relation = relation;
    }


    public RelatedToEdge(int tailIndex, HGHandle... targets) {
        this("related_to", tailIndex, targets);
    }

    public RelatedToEdge(String relation, int tailIndex, HGHandle... targets) {
        super(tailIndex, targets);
        this.relation = relation;
    }


    public RelatedToEdge(HGHandle[] head, HGHandle[] tail) {
        this("related_to", head, tail);
    }

    public RelatedToEdge(String relation, HGHandle[] head, HGHandle[] tail) {
        super(head, tail);
        this.relation = relation;
    }
}
