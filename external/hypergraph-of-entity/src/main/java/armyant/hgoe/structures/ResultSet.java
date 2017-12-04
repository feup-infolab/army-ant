package armyant.hgoe.structures;

import org.jetbrains.annotations.NotNull;

import java.util.*;

/**
 * Created by jldevezas on 2017-11-07.
 */
public class ResultSet implements Iterator<Result>, Iterable<Result> {
    private SortedSet<Result> results;
    private Map<String, Result> maxResultPerDocID;
    private Long numDocs;
    private Trace trace;
    private Iterator<Result> resultsIterator;

    public ResultSet() {
        this(new TreeSet<>((a, b) -> Double.compare(b.getScore(), a.getScore())), null, null);
    }

    public ResultSet(SortedSet<Result> results) {
        this(results, null, null);
    }

    public ResultSet(SortedSet<Result> results, Long numDocs, Trace trace) {
        this.results = results;
        this.maxResultPerDocID = new HashMap<>();
        addReplaceResults(results);
        this.numDocs = numDocs;
        this.trace = trace;
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
            numDocs = (long) results.size();
            return numDocs;
        }
        return numDocs;
    }

    public void setNumDocs(Long numDocs) {
        this.numDocs = numDocs;
    }

    public Trace getTrace() {
        return trace;
    }

    public void setTrace(Trace trace) {
        this.trace = trace;
    }

    public void unsetTrace() {
        this.trace = null;
    }

    public void addResult(Result result) {
        results.add(result);
    }

    public void addReplaceResult(Result result) {
        maxResultPerDocID.put(result.getDocID(), result);
        results.add(result);

        Result maxResult = maxResultPerDocID.get(result.getDocID());
        if (maxResult != null && result.getScore() > maxResult.getScore()) {
            results.remove(maxResult);
        }
    }

    public void addResults(SortedSet<Result> results) {
        this.results.addAll(results);
    }

    public void addReplaceResults(SortedSet<Result> results) {
        for (Result result : results) {
            addReplaceResult(result);
        }
    }

    public boolean removeResult(Result result) {
        return results.remove(result);
    }

    public boolean removeResults(List<Result> results) {
        return this.results.removeAll(results);
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

    public static ResultSet empty() {
        return new ResultSet();
    }

    @NotNull
    @Override
    public Iterator<Result> iterator() {
        return results.iterator();
    }
}
