package armyant.hgoe.inmemory;

import armyant.hgoe.HypergraphOfEntityTest;
import armyant.hgoe.exceptions.HypergraphException;
import armyant.hgoe.inmemory.nodes.TermNode;
import armyant.structures.Result;
import armyant.structures.ResultSet;
import org.testng.annotations.Test;

import java.io.IOException;

/**
 * Created by jldevezas on 2017-10-23.
 */
@Test
public class HypergraphOfEntityInMemoryTest extends HypergraphOfEntityTest {
    private String dbPath = "/tmp/hgoe-inmemory";

    public void testPrints() throws HypergraphException {
        HypergraphOfEntityInMemory hgoe = new HypergraphOfEntityInMemory(dbPath);

        System.out.println("====> Statistics");
        hgoe.printStatistics();
        System.out.print("\n");

        System.out.println("====> Nodes");
        hgoe.printNodes();
        System.out.print("\n");

        System.out.println("====> Edges");
        hgoe.printEdges();
        System.out.print("\n");

        /*System.out.println("====> Depth first traversal starting at 'Semantic search' entity");
        hgoe.printDepthFirst("Semantic search");
        System.out.print("\n");*/

        //hgoe.printDepthFirst("web");
    }

    public void testIndex() throws IOException, HypergraphException {
        HypergraphOfEntityInMemory hgoe = new HypergraphOfEntityInMemory(
                dbPath, HypergraphOfEntityInMemory.Version.BASIC, true);
        hgoe.index(document1);
        hgoe.index(document2);
        hgoe.index(document3);
        hgoe.postProcessing();
        hgoe.save();
    }

    public void testSearch() throws IOException, HypergraphException {
        HypergraphOfEntityInMemory hgoe = new HypergraphOfEntityInMemory(dbPath);

        //ResultSet resultSet = hgoe.search("web search system");
        //ResultSet resultSet = hgoe.search("Monuments of India");
        //ResultSet resultSet = hgoe.search("Poirot");
        ResultSet resultSet = hgoe.search("national park", 0, 1000);
        //ResultSet resultSet = hgoe.search("viking");
        //ResultSet resultSet = hgoe.search("viking ship");

        while (resultSet.hasNext()) {
            Result result = resultSet.next();
            System.out.println(String.format("%.4f %s", result.getScore(), result.getNode()));
        }
    }

    public void testTrace() throws IOException, HypergraphException {
        HypergraphOfEntityInMemory hgoe = new HypergraphOfEntityInMemory(dbPath);

        //ResultSet resultSet = hgoe.search("web search system");
        //ResultSet resultSet = hgoe.search("Monuments of India");
        //ResultSet resultSet = hgoe.search("Poirot");
        //ResultSet resultSet = hgoe.search("national park");
        //ResultSet resultSet = hgoe.search("viking");
        //ResultSet resultSet = hgoe.search("viking ship");
        ResultSet resultSet = hgoe.search("doom", 0, 1000);

        resultSet.getTrace().toASCII();
    }

    public void testContainsNode() throws HypergraphException {
        HypergraphOfEntityInMemory hgoe = new HypergraphOfEntityInMemory(dbPath);
        String[] terms = { "ca", "calif.", "drug" };
        for (String term: terms) {
            System.out.println(term + ": " + hgoe.containsNode(new TermNode(term)));
        }

    }
}
