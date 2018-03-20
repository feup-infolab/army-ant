//
// Created by jldevezas on 3/8/18.
//

#include <hgoe/nodes/document_node.h>

BOOST_CLASS_EXPORT_IMPLEMENT(DocumentNode)

DocumentNode::DocumentNode() = default;

DocumentNode::DocumentNode(std::string name) : Node(boost::move(name)) {}

Node::Label DocumentNode::label() const {
    return Label::DOCUMENT;
}

void DocumentNode::print(std::ostream &os) const {
    os << "DocumentNode ";
    Node::print(os);
}
