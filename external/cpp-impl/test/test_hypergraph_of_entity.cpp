//
// Created by jldevezas on 3/5/18.
//

#include <iostream>

#include <hgoe/hypergraph_of_entity.h>

int main(int argc, char **argv) {
    std::cout << "==> Testing HypergraphOfEntity" << std::endl;
    HypergraphOfEntity hg = HypergraphOfEntity("/tmp/hgoe-index");

    /*hg.index(Document("d1", "music", "I am a document about music.", {Triple {"music", "related_to", "rock"}}));
    hg.index(Document("d2", "rock music", "I am a document about rock music.",
                      {Triple {"rock", "related_to", "stoner rock"}}));*/

    hg.index(Document("1", "História1", "Era uma vez uma coisa que eu queria tokenizer, mas convenientemente.", {}));
    hg.index(Document("2", "História2", {Triple {"a", "b", "c"}, Triple {"c", "e", "f"}}));
    hg.index(
            Document("3", "História3", "Era uma vez uma coisa que eu queria tokenizer, mas convenientemente.",
                     {Triple {"a", "b", "c"}, Triple {"c", "e", "f"}}));


    hg.postProcessing();
    hg.save();

    auto resultSet = hg.search("rock", 0, 10);
    for (const auto &result : resultSet) {
        std::cout << result << std::endl;
    }

    return 0;
}
