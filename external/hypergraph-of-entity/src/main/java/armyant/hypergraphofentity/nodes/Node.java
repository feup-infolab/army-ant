package armyant.hypergraphofentity.nodes;

/**
 * Created by jldevezas on 2017-10-24.
 */
public abstract class Node {
    private String name;

    public Node() {

    }

    public Node(String name) {
        this.name = name;
    }

    public abstract String getType();

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    @Override
    public String toString() {
        return "Node{" +
               "type='" + getType() + '\'' +
               "name='" + name + '\'' +
               '}';
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;

        Node node = (Node) o;

        return name.equals(node.name);
    }

    @Override
    public int hashCode() {
        return name.hashCode();
    }
}
