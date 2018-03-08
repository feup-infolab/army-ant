//
// Created by jldevezas on 3/8/18.
//

#include <hgoe/nodes/document_node.h>

DocumentNode::DocumentNode(std::string docID) : Node(docID) {

}

NodeLabel DocumentNode::label() {
    return NodeLabel::DOCUMENT;
}