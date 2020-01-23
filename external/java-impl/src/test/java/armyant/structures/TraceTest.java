package armyant.structures;

import armyant.structures.Trace;
import org.testng.annotations.Test;

/**
 * Created by jldevezas on 2017-11-30.
 */
public class TraceTest {
    public static Trace trace = new Trace("root");

    static {
        trace.add("level 1.1");
        trace.goDown();
        trace.add("level 2.1");
        trace.add("level 2.2");
        trace.add("level 2.3");
        trace.goUp();
        trace.add("level1.2");
    }

    @Test
    public void testToASCII() {
        System.out.println(trace.toASCII());
    }

    @Test
    public void testToJSON() {
        System.out.println(trace.toJSON());
    }
}
