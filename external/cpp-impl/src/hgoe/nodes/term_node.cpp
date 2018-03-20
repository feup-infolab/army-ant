//
// Created by jldevezas on 3/8/18.
//

#include <hgoe/nodes/term_node.h>

BOOST_CLASS_EXPORT_IMPLEMENT(TermNode)

TermNode::TermNode() = default;

TermNode::TermNode(std::string name) : Node(boost::move(name)) {}

Node::Label TermNode::label() const {
    return Label::TERM;
}

void TermNode::print(std::ostream &os) const {
    os << "TermNode ";
    Node::print(os);
}
