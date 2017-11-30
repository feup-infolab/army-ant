package armyant.hgoe.structures;

import org.testng.annotations.Test;

/**
 * Created by jldevezas on 2017-11-30.
 */
@Test
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

    public void testPrint() {
        trace.print();
    }

    public void toJSON() {
        System.out.println(trace.toJSON());
    }
}
