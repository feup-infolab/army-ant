//
// Created by jldevezas on 3/8/18.
//

#ifndef ARMY_ANT_CPP_DOCUMENT_EDGE_H
#define ARMY_ANT_CPP_DOCUMENT_EDGE_H

#include <string>
#include <boost/serialization/base_object.hpp>
#include <hgoe/edges/edge.h>
#include <boost/serialization/string.hpp>
#include <boost/serialization/export.hpp>

class DocumentEdge : public Edge {
private:
    friend class boost::serialization::access;

    template<class Archive>
    void serialize(Archive &ar, unsigned int version) {
        ar & boost::serialization::base_object<Edge>(*this);
        ar & docID;
    };

    std::string docID;
public:
    DocumentEdge();

    explicit DocumentEdge(std::set<Node *, NodeComp> tail, std::set<Node *, NodeComp> head);

    DocumentEdge(std::string docID, std::set<Node *, NodeComp> tail, std::set<Node *, NodeComp> head);

    const std::string &getDocID() const;

    void setDocID(const std::string &docID);
};

BOOST_CLASS_EXPORT_KEY(DocumentEdge)

#endif //ARMY_ANT_CPP_DOCUMENT_EDGE_H
