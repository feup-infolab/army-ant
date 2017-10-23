package armyant.hypergraphofentity;

import org.apache.lucene.analysis.standard.StandardTokenizer;
import org.apache.lucene.analysis.tokenattributes.CharTermAttribute;
import org.apache.lucene.util.AttributeFactory;
import org.hypergraphdb.HGConfiguration;
import org.hypergraphdb.HGEnvironment;
import org.hypergraphdb.HyperGraph;

import java.io.IOException;
import java.io.StringReader;

/**
 * Created by jldevezas on 2017-10-23.
 */
public class HypergraphOfEntity {

    private String path;
    private HyperGraph graph;

    public HypergraphOfEntity(String path) {
        this.path = path;
    }


    public void open() {
        HGConfiguration config = new HGConfiguration();
        config.setTransactional(false);
        config.setSkipOpenedEvent(true);

        this.graph = HGEnvironment.get(this.path, config);
    }

    public void close() {
        this.graph.close();
    }

    public void indexDocument(Document document) throws IOException {
        AttributeFactory factory = AttributeFactory.DEFAULT_ATTRIBUTE_FACTORY;

        StandardTokenizer tokenizer = new StandardTokenizer(factory);
        tokenizer.setReader(new StringReader(document.getText().toLowerCase()));
        tokenizer.reset();

        CharTermAttribute attr = tokenizer.addAttribute(CharTermAttribute.class);
        while (tokenizer.incrementToken()) {
            String term = attr.toString();
            System.out.println(term);

            // TODO add to hypergraphdb
        }

    }
}
