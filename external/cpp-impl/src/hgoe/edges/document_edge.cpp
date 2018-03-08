//
// Created by jldevezas on 3/8/18.
//

#include <hgoe/edges/document_edge.h>

DocumentEdge::DocumentEdge(std::set<Node> tail, std::set<Node> head) : Edge(tail, head) {
    this->docID = std::string();
}

DocumentEdge::DocumentEdge(std::string docID, std::set<Node> tail, std::set<Node> head) : Edge(tail, head) {
    this->docID = docID;
}

const std::string &DocumentEdge::getDocID() const {
    return docID;
}

void DocumentEdge::setDocID(const std::string &docID) {
    DocumentEdge::docID = docID;
}
