package armyant.hgoe.structures;

import java.util.*;

/**
 * Created by jldevezas on 2017-11-07.
 */
public class ResultSet implements Iterator<Result> {
    private SortedSet<Result> results;
    private Long numDocs;
    private Iterator<Result> resultsIterator;

    public ResultSet() {
        this.results = new TreeSet<>((a, b) -> Double.compare(b.getScore(), a.getScore()));
        this.numDocs = null;
        this.resultsIterator = null;
    }

    public ResultSet(SortedSet<Result> results) {
        this(results, null);
    }

    public ResultSet(SortedSet<Result> results, Long numDocs) {
        this.results = results;
        this.numDocs = numDocs;
        this.resultsIterator = null;
    }

    public SortedSet<Result> getResults() {
        return results;
    }

    public void setResults(TreeSet<Result> results) {
        this.results = results;
    }

    public Long getNumDocs() {
        if (numDocs == null) {
            numDocs = (long)results.size();
            return numDocs;
        }
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

    public boolean removeResult(Result result) {
        return results.remove(result);
    }

    @Override
    public boolean hasNext() {
        if (resultsIterator == null) {
            resultsIterator = results.iterator();
        }
        return resultsIterator.hasNext();
    }

    @Override
    public Result next() {
        return resultsIterator.next();
    }
}
