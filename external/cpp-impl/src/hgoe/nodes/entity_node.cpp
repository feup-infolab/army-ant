//
// Created by jldevezas on 3/8/18.
//

#include <hgoe/nodes/entity_node.h>

EntityNode::EntityNode(std::string name) : Node(std::move(name)) {
    this->document = nullptr;
}

EntityNode::EntityNode(Document *document, std::string name) : Node(std::move(name)) {
    this->document = document;
}
