package armyant.hgoe.structures;

import armyant.hgoe.indisk.nodes.Node;

import java.util.HashMap;
import java.util.Map;

/**
 * Created by jldevezas on 2017-11-07.
 */
public class Result {
    private Object node;
    private double score;
    private Map<String, Double> components;

    public Result(Object node, double score) {
        this(node, score, null);
    }

    public Result(Object node, double score, Map<String, Double> components) {
        this.node = node;
        this.score = score;
        this.components = components;
    }

    public Object getNode() {
        return node;
    }

    public void setNode(Node node) {
        this.node = node;
    }

    public double getScore() {
        return score;
    }

    public void setScore(double score) {
        this.score = score;
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
