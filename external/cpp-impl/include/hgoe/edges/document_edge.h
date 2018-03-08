//
// Created by jldevezas on 3/8/18.
//

#ifndef ARMY_ANT_CPP_DOCUMENT_EDGE_H
#define ARMY_ANT_CPP_DOCUMENT_EDGE_H

#include <string>
#include "edge.h"

class DocumentEdge : public Edge {
private:
    std::string docID;
public:
    explicit DocumentEdge(std::set<Node> tail, std::set<Node> head);

    DocumentEdge(std::string docID, std::set<Node> tail, std::set<Node> head);

    const std::string &getDocID() const;

    void setDocID(const std::string &docID);
};

#endif //ARMY_ANT_CPP_DOCUMENT_EDGE_H
