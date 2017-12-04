package armyant.hgoe.structures;

import armyant.hgoe.structures.gson.CollectionAdapter;
import com.google.gson.*;

import java.util.ArrayList;
import java.util.Collection;
import java.util.List;

/**
 * Created by jldevezas on 2017-11-30.
 */
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

    private void printIndent(int n) {
        for (int i=0; i < n; i++) {
            System.out.print("|  ");
        }
    }

    public void print() {
        System.out.println(root.message);
        print(root.details, 0);
    }

    private void print(List<Node> children, int level) {
        for (Node child : children) {
            printIndent(level);
            System.out.println("+-- " + child.message);
            print(child.details, level + 1);
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