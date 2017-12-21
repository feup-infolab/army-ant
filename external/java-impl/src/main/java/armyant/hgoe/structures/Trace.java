package armyant.hgoe.structures;

import armyant.hgoe.structures.gson.CollectionAdapter;
import com.google.gson.*;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;

/**
 * Created by jldevezas on 2017-11-30.
 *
 * @deprecated Use armyant.structures.Trace instead
 */
@Deprecated
public class Trace {
    private Node root;
    private transient Node current;
    private transient Node last;
    private transient String rootData;

    public Trace() {
        this("Hypergraph of Entity Ranking Model Trace");
    }

    public Trace(String rootData) {
        this.rootData = rootData;

        root = new Node();
        root.message = rootData;
        root.details = new ArrayList<>();
        root.parent = null;

        current = root;
    }

    public void add(String message, Object... objects) {
        for (int i=0; i < objects.length; i++) {
            if (objects[i] instanceof String) {
                String object = (String) objects[i];
                objects[i] = object.replace("%", "%%");
            }
        }

        Node node = new Node();
        node.message = String.format(message, objects);
        node.details = new ArrayList<>();
        node.parent = current;
        current.details.add(node);
        last = node;
    }

    public void goToRoot() {
        current = root;
    }

    public void goDown() {
        current = last;
    }

    public void goUp() {
        if (current.parent != null) current = current.parent;
    }

    public void reset() {
        root = new Node();
        root.message = rootData;
        root.details = new ArrayList<>();
        root.parent = null;
        current = root;
        System.gc();
    }

    private void indent(StringBuilder builder, int n) {
        for (int i=0; i < n; i++) {
            builder.append("|  ");
        }
    }

    public String toASCII() {
        StringBuilder builder = new StringBuilder(root.message);
        builder.append('\n');
        toASCII(builder, root.details, 0);
        return builder.toString();
    }

    private void toASCII(StringBuilder builder, List<Node> children, int level) {
        for (Node child : children) {
            indent(builder, level);
            builder.append("+-- ").append(child.message).append('\n');
            toASCII(builder, child.details, level + 1);
        }
    }

    public String toJSON() {
        Gson gson = new GsonBuilder()
                .registerTypeHierarchyAdapter(Collection.class, new CollectionAdapter())
                .create();
        return gson.toJson(this.root);
    }

    public boolean isEmpty() {
        return root.details.isEmpty();
    }

    public static class Node {
        private String message;
        private transient Node parent;
        private List<Node> details;
    }
}