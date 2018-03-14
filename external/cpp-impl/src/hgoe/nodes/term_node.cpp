//
// Created by jldevezas on 3/8/18.
//

#include <hgoe/nodes/term_node.h>

BOOST_CLASS_EXPORT_IMPLEMENT(TermNode)

TermNode::TermNode() = default;

TermNode::TermNode(std::string name) : Node(boost::move(name)) {}

Node::NodeLabel TermNode::label() const {
    return NodeLabel::TERM;
}