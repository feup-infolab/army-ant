package armyant;

import it.unimi.dsi.fastutil.ints.Int2FloatOpenHashMap;
import it.unimi.dsi.fastutil.ints.Int2IntMap;
import it.unimi.dsi.fastutil.ints.Int2IntOpenHashMap;
import org.testng.annotations.Test;

/**
 * Created by jldevezas on 2018-04-05.
 */
@Test
public class EngineTest {
    public void testGetNonUniformlyAtRandom() {
        Int2FloatOpenHashMap valuesProbs = new Int2FloatOpenHashMap();
        valuesProbs.put(1, 0.1f);
        valuesProbs.put(2, 0.2f);
        valuesProbs.put(3, 0.1f);
        valuesProbs.put(4, 0.9f);
        valuesProbs.put(5, 0.9f);
        valuesProbs.put(6, 0.5f);

        int iterations = 100000;

        Int2IntOpenHashMap count = new Int2IntOpenHashMap();
        long start = System.currentTimeMillis();
        for (int i = 0; i < iterations; i++) {
            count.addTo(Engine.getNonUniformlyAtRandom(
                    valuesProbs.keySet().toIntArray(), valuesProbs.values().toFloatArray()), 1);
        }
        long end = System.currentTimeMillis();

        System.out.println(String.format("Took %d ms to generate %d random numbers", end - start, iterations));
        for (Int2IntMap.Entry entry : count.int2IntEntrySet()) {
            System.out.println(String.format("%d (%.2f%%): %d",
                    entry.getIntKey(), valuesProbs.get(entry.getIntKey()) * 100, entry.getIntValue()));
        }
    }
}
