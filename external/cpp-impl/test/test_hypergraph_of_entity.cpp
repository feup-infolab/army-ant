//
// Created by jldevezas on 3/5/18.
//

#include <iostream>

#include <hgoe/hypergraph_of_entity.h>

int main(int argc, char **argv) {
    std::cout << "==> Testing HypergraphOfEntity" << std::endl;
    HypergraphOfEntity hg = HypergraphOfEntity("/tmp/hgoe-index");
    hg.index(Document("d1", "music", "I am a document about music.", {Triple {"music", "related_to", "rock"}}));
    hg.index(Document("d2", "rock music", "I am a document about rock music.",
                      {Triple {"rock", "related_to", "stoner rock"}}));
    hg.postProcessing();
    hg.save();

    auto resultSet = hg.search("rock", 0, 10);
    for (const auto &result : resultSet) {
        std::cout << result << std::endl;
    }

    return 0;
}
