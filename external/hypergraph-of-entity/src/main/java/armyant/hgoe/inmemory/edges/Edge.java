package armyant.hgoe.inmemory.edges;

import java.io.Serializable;

/**
 * Created by jldevezas on 2017-10-24.
 */
public abstract class Edge implements Serializable {
    public Edge() {
    }

    @Override
    public String toString() {
        return this.getClass().getSimpleName();
    }
}
