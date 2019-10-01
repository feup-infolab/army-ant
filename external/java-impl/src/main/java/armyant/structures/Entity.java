package armyant.structures;

import java.util.Objects;

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

    @Override
    public boolean equals(Object o) {
        if (o == this)
            return true;
        if (!(o instanceof Entity)) {
            return false;
        }
        Entity entity = (Entity) o;
        return Objects.equals(uri, entity.uri);
    }

    @Override
    public int hashCode() {
        return Objects.hash(uri);
    }
}