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
    private static final int RANDOM_ITERATIONS = 50_000_000;
    private static final Int2FloatOpenHashMap valuesProbs = new Int2FloatOpenHashMap();

    static {
        valuesProbs.put(0, 1f);
        valuesProbs.put(1, 0.1f);
        valuesProbs.put(2, 0.2f);
        valuesProbs.put(3, 0.1f);
        valuesProbs.put(4, 0.9f);
        valuesProbs.put(5, 0.9f);
        valuesProbs.put(6, 0.5f);
    }

    public void testSampleNonUniformlyAtRandom() {
        Int2IntOpenHashMap count = new Int2IntOpenHashMap();
        long start = System.currentTimeMillis();
        for (int i = 0; i < RANDOM_ITERATIONS; i++) {
            count.addTo(Engine.sampleNonUniformlyAtRandom(
                    valuesProbs.keySet().toIntArray(), valuesProbs.values().toFloatArray()), 1);
        }
        long end = System.currentTimeMillis();

        for (Int2IntMap.Entry entry : count.int2IntEntrySet()) {
            System.out.println(String.format("%d (%.2f%%): %d",
                    entry.getIntKey(), valuesProbs.get(entry.getIntKey()) * 100, entry.getIntValue()));
        }

        System.out.println(String.format(
                "Took %,dms to sample %,d random elements non-uniformly at random", end - start, RANDOM_ITERATIONS));
    }

    public void testSampleUniformlyAtRandom() {
        Int2IntOpenHashMap count = new Int2IntOpenHashMap();
        long start = System.currentTimeMillis();
        for (int i = 0; i < RANDOM_ITERATIONS; i++) {
            count.addTo(Engine.sampleUniformlyAtRandom(valuesProbs.keySet().toIntArray()), 1);
        }
        long end = System.currentTimeMillis();

        for (Int2IntMap.Entry entry : count.int2IntEntrySet()) {
            System.out.println(String.format("%d (%.2f%%): %d",
                    entry.getIntKey(), valuesProbs.get(entry.getIntKey()) * 100, entry.getIntValue()));
        }

        System.out.println(String.format(
                "Took %,dms to sample %,d random elements uniformly at random", end - start, RANDOM_ITERATIONS));
    }
}
