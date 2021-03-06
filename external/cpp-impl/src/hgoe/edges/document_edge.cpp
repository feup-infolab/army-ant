//
// Created by jldevezas on 3/8/18.
//

#include <hgoe/edges/document_edge.h>

BOOST_CLASS_EXPORT_IMPLEMENT(DocumentEdge)

DocumentEdge::DocumentEdge() = default;

DocumentEdge::DocumentEdge(NodeSet tail, NodeSet head) : Edge(boost::move(tail), boost::move(head)) { }

DocumentEdge::DocumentEdge(std::string docID, NodeSet tail, NodeSet head) : Edge(boost::move(tail), boost::move(head)) {
    this->docID = boost::move(docID);
}

bool DocumentEdge::doCompare(const Edge &rhs) const {
    const auto rhsDocumentEdge = dynamic_cast<const DocumentEdge *>(&rhs);
    return docID == rhsDocumentEdge->docID;
}

std::size_t DocumentEdge::doHash() const {
    std::size_t h = 0;
    boost::hash_combine(h, docID);
    boost::hash_combine(h, Edge::doHash());
    return h;
}

void DocumentEdge::print(std::ostream &os) const {
    os << "DocumentEdge { docID: " << (docID.empty() ?  "N/A" : docID) << " } & ";
    Edge::print(os);
}

const std::string &DocumentEdge::getDocID() const {
    return docID;
}

void DocumentEdge::setDocID(const std::string &docID) {
    DocumentEdge::docID = docID;
}

Edge::Label DocumentEdge::label() const {
    return Label::DOCUMENT;
}