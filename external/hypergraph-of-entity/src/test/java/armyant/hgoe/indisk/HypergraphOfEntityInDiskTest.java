package armyant.hgoe.indisk;

import armyant.hgoe.HypergraphOfEntityTest;
import armyant.hgoe.structures.Result;
import armyant.hgoe.structures.ResultSet;
import org.testng.annotations.Test;

import java.io.IOException;

/**
 * Created by jldevezas on 2017-10-23.
 */
@Test
public class HypergraphOfEntityInDiskTest extends HypergraphOfEntityTest {
    private String dbPath = "/tmp/test-hgoe";

    public void testPrints() {
        HypergraphOfEntityInDisk hgoe = new HypergraphOfEntityInDisk(dbPath);

        System.out.println("====> Statistics");
        hgoe.printStatistics();
        System.out.print("\n");

        System.out.println("====> Nodes");
        hgoe.printNodes();
        System.out.print("\n");

        System.out.println("====> Edges");
        hgoe.printEdges();
        System.out.print("\n");

        System.out.println("====> Depth first traversal starting at 'Semantic search' entity");
        hgoe.printDepthFirst("Semantic search");
        System.out.print("\n");

        //hgoe.printDepthFirst("web");
    }

    public void testIndex() throws IOException {
        HypergraphOfEntityInDisk hgoe = new HypergraphOfEntityInDisk(dbPath, true);
        hgoe.index(document1);
        hgoe.index(document2);
        hgoe.index(document3);
        testPrints();
        hgoe.close();
    }

    public void testSearch() throws IOException {
        //HypergraphOfEntityInDisk hgoe = new HypergraphOfEntityInDisk(dbPath);
        HypergraphOfEntityInDisk hgoe = new HypergraphOfEntityInDisk("/tmp/hgoe");

        //ResultSet resultSet = hgoe.search("web search system");
        //ResultSet resultSet = hgoe.search("Monuments of India");
        ResultSet resultSet = hgoe.search("Poirot");
        //ResultSet resultSet = hgoe.search("national park");

        for (ResultSet it = resultSet; it.hasNext(); ) {
            Result result = it.next();
            System.out.println(String.format("%.4f %s", result.getScore(), result.getNode()));
        }

        hgoe.close();
    }

}
