# Configuration

## Gremlin Server

We provide configuration files for Apache Tinkerpop Gremlin Server 3.2.4 for using the `GraphOfWord` and `GraphOfEntity` engines. Nota that you can use symbolic links instead of copying the files, in order to keep everything under the Army ANT directory. Also, you need to create an `/opt/army-ant` data directory and/or edit the `neo4j*.properties` files to point to the correct database directories. The list of relevant configuration files includes:

* /opt/apache-tinkerpop-gremlin-server-3.2.4/conf/gremlin-server-neo4j-graph-of-word.yaml
* /opt/apache-tinkerpop-gremlin-server-3.2.4/conf/gremlin-server-neo4j-graph-of-entity.yaml
* /opt/apache-tinkerpop-gremlin-server-3.2.4/conf/neo4j-graph-of-word.properties
* /opt/apache-tinkerpop-gremlin-server-3.2.4/conf/neo4j-graph-of-entity.properties
* /opt/apache-tinkerpop-gremlin-server-3.2.4/scripts/army-ant.groovy
