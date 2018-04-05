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
    private static final int RANDOM_ITERATIONS = 100000;
    private static final Int2FloatOpenHashMap valuesProbs = new Int2FloatOpenHashMap();

    static {
        valuesProbs.put(1, 0.1f);
        valuesProbs.put(2, 0.2f);
        valuesProbs.put(3, 0.1f);
        valuesProbs.put(4, 0.9f);
        valuesProbs.put(5, 0.9f);
        valuesProbs.put(6, 0.5f);
    }

    public void testGetNonUniformlyAtRandom() {
        Int2IntOpenHashMap count = new Int2IntOpenHashMap();
        long start = System.currentTimeMillis();
        for (int i = 0; i < RANDOM_ITERATIONS; i++) {
            count.addTo(Engine.getNonUniformlyAtRandom(
                    valuesProbs.keySet().toIntArray(), valuesProbs.values().toFloatArray()), 1);
        }
        long end = System.currentTimeMillis();

        System.out.println(String.format(
                "Took %d ms to generate %d random numbers non-uniformly at random", end - start, RANDOM_ITERATIONS));
        for (Int2IntMap.Entry entry : count.int2IntEntrySet()) {
            System.out.println(String.format("%d (%.2f%%): %d",
                    entry.getIntKey(), valuesProbs.get(entry.getIntKey()) * 100, entry.getIntValue()));
        }
    }

    public void testGetUniformlyAtRandom() {
        Int2IntOpenHashMap count = new Int2IntOpenHashMap();
        long start = System.currentTimeMillis();
        for (int i = 0; i < RANDOM_ITERATIONS; i++) {
            count.addTo(Engine.getUniformlyAtRandom(valuesProbs.keySet().toIntArray()), 1);
        }
        long end = System.currentTimeMillis();

        System.out.println(String.format(
                "Took %d ms to generate %d random numbers uniformly at random", end - start, RANDOM_ITERATIONS));
        for (Int2IntMap.Entry entry : count.int2IntEntrySet()) {
            System.out.println(String.format("%d (%.2f%%): %d",
                    entry.getIntKey(), valuesProbs.get(entry.getIntKey()) * 100, entry.getIntValue()));
        }
    }
}
