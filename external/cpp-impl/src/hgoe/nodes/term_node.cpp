//
// Created by jldevezas on 3/8/18.
//

#include <hgoe/nodes/term_node.h>

BOOST_CLASS_EXPORT_IMPLEMENT(TermNode)

TermNode::TermNode() {

}

TermNode::TermNode(std::string name) : Node(name) {

}

NodeLabel TermNode::label() {
    return NodeLabel::TERM;
}