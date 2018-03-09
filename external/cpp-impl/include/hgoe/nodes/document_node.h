//
// Created by jldevezas on 3/8/18.
//

#ifndef ARMY_ANT_CPP_DOCUMENT_NODE_H
#define ARMY_ANT_CPP_DOCUMENT_NODE_H

#include <hgoe/nodes/node.h>
#include <boost/serialization/base_object.hpp>
#include <boost/serialization/export.hpp>

class DocumentNode : public Node {
private:
    friend class boost::serialization::access;

    template<class Archive>
    void serialize(Archive &ar, unsigned int version) {
        ar & boost::serialization::base_object<Node>(*this);
    };
public:
    DocumentNode();

    explicit DocumentNode(std::string name);

    NodeLabel label() override;
};

BOOST_CLASS_EXPORT_KEY(DocumentNode)

#endif //ARMY_ANT_CPP_DOCUMENT_NODE_H
