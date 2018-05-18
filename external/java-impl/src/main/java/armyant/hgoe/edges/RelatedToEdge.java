package armyant.hgoe.edges;

/**
 * Created by jldevezas on 2017-10-25.
 */
public class RelatedToEdge extends Edge {
    private String relation;

    public RelatedToEdge() {
        this("related_to");
    }

    public RelatedToEdge(String relation) {
        super();
        this.relation = relation;
    }
}
