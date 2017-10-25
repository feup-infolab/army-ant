package armyant.hypergraphofentity.edges;

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
}
