package armyant.hgoe.structures;

import com.google.gson.*;

import java.lang.reflect.Type;
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

    public Trace() {
        this("Hypergraph of Entity Ranking Model Trace");
    }

    public Trace(String rootData) {
        root = new Node();
        root.message = rootData;
        root.children = new ArrayList<>();
        root.parent = null;
        current = root;
    }

    public void add(String message, Object... objects) {
        Node node = new Node();
        node.message = String.format(message, objects);
        node.children = new ArrayList<>();
        node.parent = current;
        current.children.add(node);
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

    private void printIndent(int n) {
        for (int i=0; i < n; i++) {
            System.out.print("|  ");
        }
    }

    public void print() {
        System.out.println(root.message);
        print(root.children, 0);
    }

    private void print(List<Node> children, int level) {
        for (Node child : children) {
            printIndent(level);
            System.out.println("+-- " + child.message);
            print(child.children, level+1);
        }
    }

    public String toJSON() {
        Gson gson = new GsonBuilder().registerTypeHierarchyAdapter(Collection.class, new CollectionAdapter()).create();
        return gson.toJson(this.root);
    }

    public static class Node {
        private String message;
        private transient Node parent;
        private List<Node> children;
    }

    class CollectionAdapter implements JsonSerializer<Collection<?>> {
        @Override
        public JsonElement serialize(Collection<?> src, Type typeOfSrc, JsonSerializationContext context) {
            if (src == null || src.isEmpty()) // exclusion is made here
                return null;

            JsonArray array = new JsonArray();

            for (Object child : src) {
                JsonElement element = context.serialize(child);
                array.add(element);
            }

            return array;
        }
    }
}