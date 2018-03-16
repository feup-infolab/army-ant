//
// Created by jldevezas on 3/8/18.
//

#ifndef ARMY_ANT_CPP_DOCUMENT_EDGE_H
#define ARMY_ANT_CPP_DOCUMENT_EDGE_H

#include <string>
#include <hgoe/edges/edge.h>
#include <boost/serialization/string.hpp>
#include <boost/serialization/base_object.hpp>
#include <boost/serialization/export.hpp>
#include <ostream>

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

    explicit DocumentEdge(NodeSet tail, NodeSet head);

    DocumentEdge(std::string docID, NodeSet tail, NodeSet head);

    bool doCompare(const Edge &rhs) const override;

    std::size_t doHash() const override;

    void print(std::ostream &os) const override;

    const std::string &getDocID() const;

    void setDocID(const std::string &docID);

    Label label() const override;
};

BOOST_CLASS_EXPORT_KEY(DocumentEdge)

#endif //ARMY_ANT_CPP_DOCUMENT_EDGE_H
