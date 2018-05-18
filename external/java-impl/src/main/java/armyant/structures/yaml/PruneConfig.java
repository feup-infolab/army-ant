package armyant.structures.yaml;

import armyant.hgoe.edges.Edge;
import armyant.hgoe.nodes.Node;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.dataformat.yaml.YAMLFactory;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;

/**
 * Created by jldevezas on 2018-04-05.
 */
public class PruneConfig {
    private Map<String, Map<String, Float>> thresholds;

    public static PruneConfig load(String path) throws IOException {
        return load(new File(path));
    }

    public static PruneConfig load(File file) throws IOException {
        if (!file.exists()) throw new FileNotFoundException(file.getAbsolutePath());
        ObjectMapper mapper = new ObjectMapper(new YAMLFactory());
        return mapper.readValue(file, PruneConfig.class);
    }

    public Map<String, Map<String, Float>> getThresholds() {
        return thresholds;
    }

    public void setThresholds(Map<String, Map<String, Float>> thresholds) {
        this.thresholds = thresholds;
    }

    public Float getNodeThreshold(Class<? extends Node> nodeClass) {
        return thresholds
                .getOrDefault("nodes", new HashMap<>())
                .getOrDefault(nodeClass.getSimpleName(), 0f);
    }

    public Float getEdgeThreshold(Class<? extends Edge> edgeClass) {
        return thresholds
                .getOrDefault("edges", new HashMap<>())
                .getOrDefault(edgeClass.getSimpleName(), 0f);
    }
}
