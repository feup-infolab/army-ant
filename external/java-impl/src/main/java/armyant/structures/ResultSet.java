package armyant.structures;

import org.apache.commons.collections4.bag.TreeBag;
import org.jetbrains.annotations.NotNull;

import java.util.*;

/**
 * Created by jldevezas on 2017-11-07.
 */
public class ResultSet implements Iterator<Result>, Iterable<Result> {
    private TreeBag<Result> results;
    private Map<String, Result> maxResultPerDocID;
    private Long numDocs;
    private Trace trace;
    private Iterator<Result> resultsIterator;

    public static ResultSet empty() {
        return new ResultSet();
    }

    public ResultSet() {
        this(new TreeBag<>((a, b) -> Comparator
            .comparing(Result::getScore)
            //.thenComparing(Result::getID)
            .compare(b, a)), null, null);
    }

    public ResultSet(TreeBag<Result> results) {
        this(results, null, null);
    }

    public ResultSet(TreeBag<Result> results, Long numDocs, Trace trace) {
        this.results = results;
        this.maxResultPerDocID = new HashMap<>();
        addReplaceResults(results);
        this.numDocs = numDocs;
        this.trace = trace;
        this.resultsIterator = null;
    }

    public TreeBag<Result> getResults() {
        return results;
    }

    public void setResults(TreeBag<Result> results) {
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
        maxResultPerDocID.put(result.getID(), result);
        results.add(result);

        Result maxResult = maxResultPerDocID.get(result.getID());
        if (maxResult != null && result.getScore() > maxResult.getScore()) {
            results.remove(maxResult);
        }
    }

    public void addResults(TreeBag<Result> results) {
        this.results.addAll(results);
    }

    public void addReplaceResults(TreeBag<Result> results) {
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

    public int size() {
        return this.results.size();
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

    public boolean isEmpty() {
        return this.results.isEmpty();
    }

    @NotNull
    @Override
    public Iterator<Result> iterator() {
        return results.iterator();
    }
}
