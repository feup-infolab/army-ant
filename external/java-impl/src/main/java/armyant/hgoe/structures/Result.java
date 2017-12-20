package armyant.hgoe.structures;

import armyant.hgoe.indisk.nodes.Node;

import java.util.HashMap;
import java.util.Map;
import java.util.Set;

/**
 * Created by jldevezas on 2017-11-07.
 *
 * @deprecated Use armyant.structures.Result instead
 */
@Deprecated
public class Result {
    private double score;
    private Object node;
    private String docID;
    private Map<String, Double> components;

    public Result(double score, Object node) {
        this(score, node, null, null);
    }

    public Result(double score, Object node, String docID) {
        this(score, node, docID, null);
    }

    public Result(double score, Object node, String docID, Map<String, Double> components) {
        this.node = node;
        this.score = score;
        this.docID = docID;
        this.components = components;
    }

    public double getScore() {
        return score;
    }

    public void setScore(double score) {
        this.score = score;
    }

    public Object getNode() {
        return node;
    }

    public void setNode(Node node) {
        this.node = node;
    }

    public String getDocID() {
        return docID;
    }

    public void setDocID(String docID) {
        this.docID = docID;
    }

    public Map<String, Double> getComponents() {
        return components;
    }

    public void setComponents(Map<String, Double> components) {
        this.components = components;
    }

    public void setComponent(String key, Double value) {
        if (this.components == null) {
            this.components = new HashMap<>();
        }

        this.components.put(key, value);
    }

    public void unsetComponent(String key) {
        this.components.remove(key);
        if (this.components.isEmpty()) {
            this.components = null;
        }
    }
}
