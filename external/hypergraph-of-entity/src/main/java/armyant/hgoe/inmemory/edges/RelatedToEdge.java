package armyant.hgoe.inmemory.edges;

import java.io.Serializable;

/**
 * Created by jldevezas on 2017-10-25.
 */
public class RelatedToEdge extends Edge implements Serializable {
    private String relation;

    public RelatedToEdge() {
        this("related_to");
    }

    public RelatedToEdge(String relation) {
        super();
        this.relation = relation;
    }
}
