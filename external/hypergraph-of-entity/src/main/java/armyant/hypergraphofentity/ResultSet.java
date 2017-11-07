package armyant.hypergraphofentity;

import java.util.ArrayList;
import java.util.List;

/**
 * Created by jldevezas on 2017-11-07.
 */
public class ResultSet {
    private List<Result> results;
    private Long numDocs;

    public ResultSet() {
        this.results = new ArrayList<>();
        this.numDocs = null;
    }

    public ResultSet(List<Result> results) {
        this.results = results;
        this.numDocs = null;
    }

    public ResultSet(List<Result> results, Long numDocs) {
        this.results = results;
        this.numDocs = numDocs;
    }

    public List<Result> getResults() {
        return results;
    }

    public void setResults(List<Result> results) {
        this.results = results;
    }

    public Long getNumDocs() {
        return numDocs;
    }

    public void setNumDocs(Long numDocs) {
        this.numDocs = numDocs;
    }

    public void addResults(List<Result> results) {
        this.results.addAll(results);
    }

    public boolean removeResults(List<Result> results) {
        return this.results.removeAll(results);
    }

    public void addResult(Result result) {
        results.add(result);
    }

    public Result removeResult(int i) {
        return results.remove(i);
    }
}
