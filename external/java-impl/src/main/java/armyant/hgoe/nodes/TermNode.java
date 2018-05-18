package armyant.hgoe.nodes;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Created by jldevezas on 2017-10-24.
 */
public class TermNode extends RankableNode {
    private static final Logger logger = LoggerFactory.getLogger(TermNode.class);

    public TermNode() {
    }

    public TermNode(String name) {
        super(name);
    }

    @Override
    public void setID(String id) {
        logger.warn("Ignoring: the term ID is the term itself, so it cannot be changed");
    }

    @Override
    public String getID() {
        return name;
    }
}
