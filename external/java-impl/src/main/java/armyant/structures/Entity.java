package armyant.structures;

public class Entity {
    private String uri;
    private String label;

    public Entity(String label) {
        this(label, null);
    }

    public Entity(String label, String uri) {
        this.uri = uri;
        this.label = label;
    }

    public String getURI() {
        return uri;
    }

    public void setURI(String uri) {
        this.uri = uri;
    }

    public String getLabel() {
        return label;
    }

    public void setLabel(String label) {
        this.label = label;
    }
}