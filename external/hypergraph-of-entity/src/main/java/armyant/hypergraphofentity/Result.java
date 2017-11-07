package armyant.hypergraphofentity;

import java.util.HashMap;
import java.util.Map;

/**
 * Created by jldevezas on 2017-11-07.
 */
public class Result {
    private String docID;
    private double score;
    private Map<String, Double> components;

    public Result(String docID, double score) {
        this(docID, score, null);
    }

    public Result(String docID, double score, Map<String, Double> components) {
        this.docID = docID;
        this.score = score;
        this.components = components;
    }

    public String getDocID() {
        return docID;
    }

    public void setDocID(String docID) {
        this.docID = docID;
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
