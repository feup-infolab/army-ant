package armyant.hgoe.indisk.edges;

import org.hypergraphdb.HGHandle;

/**
 * Created by jldevezas on 2017-10-25.
 */
public class ContainedInEdge extends Edge {
    public ContainedInEdge() {
    }

    public ContainedInEdge(HGHandle... outgoingSet) {
        super(outgoingSet);
    }

    public ContainedInEdge(int tailIndex, HGHandle... targets) {
        super(tailIndex, targets);
    }

    public ContainedInEdge(HGHandle[] head, HGHandle[] tail) {
        super(head, tail);
    }
}
