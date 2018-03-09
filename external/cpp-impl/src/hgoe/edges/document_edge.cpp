//
// Created by jldevezas on 3/8/18.
//

#include <hgoe/edges/document_edge.h>

BOOST_CLASS_EXPORT_IMPLEMENT(DocumentEdge)

DocumentEdge::DocumentEdge() = default;

DocumentEdge::DocumentEdge(std::set<Node *> tail, std::set<Node *> head) : Edge(std::move(tail), std::move(head)) {
    this->docID = std::string();
}

DocumentEdge::DocumentEdge(std::string docID, std::set<Node *> tail, std::set<Node *> head) :
        Edge(std::move(tail), std::move(head)) {
    this->docID = std::move(docID);
}

const std::string &DocumentEdge::getDocID() const {
    return docID;
}

void DocumentEdge::setDocID(const std::string &docID) {
    DocumentEdge::docID = docID;
}