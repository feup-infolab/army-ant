package armyant.hgoe.edges;

import java.io.Serializable;

import armyant.hgoe.Atom;

/**
 * Created by jldevezas on 2017-10-24.
 */
public class Edge implements Atom, Serializable {
    public Edge() {
    }

    @Override
    public String toString() {
        return this.getClass().getSimpleName();
    }
}
