package armyant.structures.yaml;

import armyant.hgoe.edges.*;
import armyant.hgoe.nodes.EntityNode;
import armyant.hgoe.nodes.TermNode;
import org.testng.annotations.Test;

import java.io.IOException;

/**
 * Created by jldevezas on 2018-04-05.
 */
@Test
public class PruneConfigTest {
    public void loadTest() throws IOException {
        PruneConfig pruneConfig = PruneConfig.load("/opt/army-ant/features/inex_2009_3t_nl/prune.yml");

        System.out.println(pruneConfig.getNodeThreshold(TermNode.class));
        System.out.println(pruneConfig.getNodeThreshold(EntityNode.class));

        System.out.println(pruneConfig.getEdgeThreshold(DocumentEdge.class));
        System.out.println(pruneConfig.getEdgeThreshold(RelatedToEdge.class));
        System.out.println(pruneConfig.getEdgeThreshold(ContainedInEdge.class));
        System.out.println(pruneConfig.getEdgeThreshold(SynonymEdge.class));
        System.out.println(pruneConfig.getEdgeThreshold(ContextEdge.class));
    }
}
