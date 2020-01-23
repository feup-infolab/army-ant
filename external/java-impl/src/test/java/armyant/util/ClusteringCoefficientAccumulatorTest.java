package armyant.util;

import org.testng.annotations.Test;

/**
 * Created by José Devezas
 * 2019-05-31
 */
public class ClusteringCoefficientAccumulatorTest {
    @Test
    public void testAddClusteringCoefficient() {
        ClusteringCoefficientAccumulator accumulator = new ClusteringCoefficientAccumulator(1/3f);
        accumulator = accumulator.addClusteringCoefficient(new ClusteringCoefficientAccumulator(1/3f));
        accumulator = accumulator.addClusteringCoefficient(1/3f);
        assert accumulator.getAvgClusteringCoefficient() == 1/3f
                : "Average is " + accumulator.getAvgClusteringCoefficient() + ", but it should be 1/3f";
    }
}