package armyant.hypergraphofentity.edges;

import org.hypergraphdb.HGHandle;
import org.hypergraphdb.HGPlainLink;
import org.hypergraphdb.atom.HGBergeLink;

import java.util.Arrays;
import java.util.stream.Collectors;

/**
 * Created by jldevezas on 2017-10-24.
 */
public abstract class Edge extends HGBergeLink {
    public Edge() {
    }

    public Edge(HGHandle... outgoingSet) {
        super(outgoingSet);
    }

    public Edge(int tailIndex, HGHandle... targets) {
        super(tailIndex, targets);
    }

    public Edge(HGHandle[] head, HGHandle[] tail) {
        super(head, tail);
    }

    @Override
    public String toString() {
        return this.getClass().getSimpleName() + "{" +
               String.join(",", Arrays.stream(outgoingSet).map(HGHandle::toString).collect(Collectors.toList())) +
               '}';
    }
}
