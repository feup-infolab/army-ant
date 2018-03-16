//
// Created by jldevezas on 3/8/18.
//

#include <hgoe/nodes/entity_node.h>

BOOST_CLASS_EXPORT_IMPLEMENT(EntityNode)

EntityNode::EntityNode() {

}

EntityNode::EntityNode(std::string name) : Node(boost::move(name)) {
    this->docID = nullptr;
}

EntityNode::EntityNode(Document *document, std::string name) : Node(boost::move(name)) {
    if (name == document->getTitle()) {
        this->docID = boost::make_shared<std::string>(document->getDocID());
    } else {
        this->docID = nullptr;
    }
}

Node::Label EntityNode::label() const {
    return Label::ENTITY;
}

void EntityNode::setDocID(std::string &docID) {
    this->docID = boost::make_shared<std::string>(docID);
}

std::string EntityNode::getDocID() const {
    return *docID;
}

bool EntityNode::hasDocID() {
    return docID != nullptr;
}
