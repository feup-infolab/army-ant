package armyant.util;

/**
 * Created by José Devezas
 * 2019-05-31
 */
public class ClusteringCoefficientAccumulator {
    private float sumClusteringCoefficient;
    private int lenClusteringCoefficients;

    public ClusteringCoefficientAccumulator() {
        sumClusteringCoefficient = 0;
        lenClusteringCoefficients = 0;
    }

    public ClusteringCoefficientAccumulator(float clusteringCoefficient) {
        sumClusteringCoefficient = clusteringCoefficient;
        lenClusteringCoefficients = 1;
    }

    public ClusteringCoefficientAccumulator addClusteringCoefficient(float clusteringCoefficient) {
        sumClusteringCoefficient += clusteringCoefficient;
        lenClusteringCoefficients++;
        return this;
    }

    public ClusteringCoefficientAccumulator addClusteringCoefficient(ClusteringCoefficientAccumulator accumulator) {
        sumClusteringCoefficient += accumulator.sumClusteringCoefficient;
        lenClusteringCoefficients += accumulator.lenClusteringCoefficients;
        return this;
    }

    public int size() {
        return lenClusteringCoefficients;
    }

    public float getAvgClusteringCoefficient() {
        return sumClusteringCoefficient / lenClusteringCoefficients;
    }

    public ClusteringCoefficientAccumulator getAvgClusteringCoefficientAsAccumulator() {
        return new ClusteringCoefficientAccumulator(sumClusteringCoefficient / lenClusteringCoefficients);
    }
}