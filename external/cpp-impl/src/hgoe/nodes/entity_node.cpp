//
// Created by jldevezas on 3/8/18.
//

#include <hgoe/nodes/entity_node.h>

BOOST_CLASS_EXPORT_IMPLEMENT(EntityNode)

EntityNode::EntityNode() = default;

EntityNode::EntityNode(std::string name) : Node(boost::move(name)) { }

EntityNode::EntityNode(Document *document, std::string name) : Node(name) {
    if (name == document->getTitle()) {
        this->docID = document->getDocID();
    }
}

Node::Label EntityNode::label() const {
    return Label::ENTITY;
}

void EntityNode::setDocID(const std::string &docID) {
    this->docID = docID;
}

std::string EntityNode::getDocID() const {
    return docID;
}

bool EntityNode::hasDocID() {
    return !docID.empty();
}

void EntityNode::print(std::ostream &os) const {
    os << "EntityNode { docID: " << (docID.empty() ?  "N/A" : docID) << " } & ";
    Node::print(os);
}
