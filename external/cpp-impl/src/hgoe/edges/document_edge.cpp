//
// Created by jldevezas on 3/8/18.
//

#include <hgoe/edges/document_edge.h>

BOOST_CLASS_EXPORT_IMPLEMENT(DocumentEdge)

DocumentEdge::DocumentEdge() = default;

DocumentEdge::DocumentEdge(NodeSet tail, NodeSet head) :
        Edge(boost::move(tail), boost::move(head)) {
    this->docID = std::string();
}

DocumentEdge::DocumentEdge(std::string docID, NodeSet tail, NodeSet head) :
        Edge(boost::move(tail), boost::move(head)) {
    this->docID = boost::move(docID);
}

bool DocumentEdge::doCompare(const Edge &rhs) const {
    const auto rhsDocumentEdge = dynamic_cast<const DocumentEdge *>(&rhs);
    return docID == rhsDocumentEdge->docID;
}

const std::string &DocumentEdge::getDocID() const {
    return docID;
}

void DocumentEdge::setDocID(const std::string &docID) {
    DocumentEdge::docID = docID;
}

Edge::EdgeLabel DocumentEdge::label() const {
    return EdgeLabel::DOCUMENT;
}
