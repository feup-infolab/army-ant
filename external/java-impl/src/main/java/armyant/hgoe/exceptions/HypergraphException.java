package armyant.hgoe.exceptions;

/**
 * Created by jldevezas on 2017-11-17.
 */
public class HypergraphException extends Exception {
    public HypergraphException() {
    }

    public HypergraphException(String s) {
        super(s);
    }

    public HypergraphException(String s, Throwable throwable) {
        super(s, throwable);
    }

    public HypergraphException(Throwable throwable) {
        super(throwable);
    }

    public HypergraphException(String s, Throwable throwable, boolean b, boolean b1) {
        super(s, throwable, b, b1);
    }
}
