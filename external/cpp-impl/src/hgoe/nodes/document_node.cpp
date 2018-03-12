//
// Created by jldevezas on 3/8/18.
//

#include <hgoe/nodes/document_node.h>

BOOST_CLASS_EXPORT_IMPLEMENT(DocumentNode)

DocumentNode::DocumentNode() = default;

DocumentNode::DocumentNode(std::string name) : Node(std::move(name)) {}

NodeLabel DocumentNode::label() const {
    return NodeLabel::DOCUMENT;
}