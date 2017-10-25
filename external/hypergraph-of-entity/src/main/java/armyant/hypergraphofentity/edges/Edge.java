package armyant.hypergraphofentity.edges;

import org.hypergraphdb.HGHandle;
import org.hypergraphdb.HGPlainLink;

/**
 * Created by jldevezas on 2017-10-24.
 */
public abstract class Edge extends HGPlainLink {
    public Edge() {
    }

    public Edge(HGHandle... outgoingSet) {
        super(outgoingSet);
    }
}
