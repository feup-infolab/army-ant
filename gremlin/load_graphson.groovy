import org.apache.tinkerpop.gremlin.spark.process.computer.SparkGraphComputer
import org.apache.tinkerpop.gremlin.giraph.process.computer.GiraphGraphComputer

load_graphson: {
  readGraphConf = new PropertiesConfiguration()
  readGraphConf.load('conf/hadoop-graph/army-ant-load.properties')
  readGraphConf.setProperty('gremlin.hadoop.inputLocation', graphsonPath)
  graph = GraphFactory.open(readGraphConf)
  
  blvp = BulkLoaderVertexProgram.build()
    .keepOriginalIds(false)
    .writeGraph("conf/army-ant-cassandra-es-${indexPath}.properties")
    .create(graph)
  
  graph.compute(SparkGraphComputer).program(blvp).submit().get()
  //graph.compute(GiraphGraphComputer).program(blvp).submit().get()
}
