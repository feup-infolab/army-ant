//
// Created by jldevezas on 3/8/18.
//

#include <hgoe/nodes/entity_node.h>

BOOST_CLASS_EXPORT_IMPLEMENT(EntityNode)

EntityNode::EntityNode() {

}

EntityNode::EntityNode(std::string name) : Node(boost::move(name)) {
    this->document = nullptr;
}

EntityNode::EntityNode(Document *document, std::string name) : Node(boost::move(name)) {
    this->document = document;
}

Node::NodeLabel EntityNode::label() const {
    return NodeLabel::ENTITY;
}