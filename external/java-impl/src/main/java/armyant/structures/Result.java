package armyant.structures;

import java.util.HashMap;
import java.util.Map;

/**
 * Created by jldevezas on 2017-11-07.
 */
public class Result {
    private double score;
    private String id;
    private String name;
    private String type;
    private Map<String, Double> components;

    public Result(double score, String id, String name) {
        this(score, id, name, "document");
    }

    public Result(double score, String id, String name, String type) {
        this(score, id, name, type, null);
    }

    public Result(double score, String id, String name, String type, Map<String, Double> components) {
        this.score = score;
        this.id = id;
        this.name = name;
        this.type = type;
        this.components = components;
    }

    public double getScore() {
        return score;
    }

    public void setScore(double score) {
        this.score = score;
    }

    public String getID() {
        return id;
    }

    public void setID(String id) {
        this.id = id;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getType() {
        return type;
    }

    public void setType(String type) {
        this.type = type;
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
