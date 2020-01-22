package armyant.structures.yaml;

import java.io.File;
import java.io.FileNotFoundException;
import java.io.IOException;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.dataformat.yaml.YAMLFactory;

/**
 * Created by jldevezas on 2018-04-05.
 */
public class TFBinsConfig {
    private Integer bins;

    public static TFBinsConfig load(String path) throws IOException {
        return load(new File(path));
    }

    public static TFBinsConfig load(File file) throws IOException {
        if (!file.exists()) throw new FileNotFoundException(file.getAbsolutePath());
        ObjectMapper mapper = new ObjectMapper(new YAMLFactory());
        return mapper.readValue(file, TFBinsConfig.class);
    }

    public Integer getBins() {
        return bins;
    }

    public void setBins(int bins) {
        this.bins = bins;
    }
}
