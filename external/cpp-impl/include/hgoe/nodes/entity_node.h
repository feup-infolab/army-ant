//
// Created by jldevezas on 3/8/18.
//

#ifndef ARMY_ANT_CPP_ENTITY_NODE_H
#define ARMY_ANT_CPP_ENTITY_NODE_H

#include <structures/document.h>
#include <hgoe/nodes/node.h>
#include <boost/serialization/base_object.hpp>
#include <boost/serialization/export.hpp>

class EntityNode : public Node {
private:
    friend class boost::serialization::access;

    template<class Archive>
    void serialize(Archive &ar, unsigned int version) {
        ar & boost::serialization::base_object<Node>(*this);
    };

    Document *document;
public:
    EntityNode();

    explicit EntityNode(std::string name);

    EntityNode(Document *document, std::string name);

    NodeLabel label() const override;
};

BOOST_CLASS_EXPORT_KEY(EntityNode)

#endif //ARMY_ANT_CPP_ENTITY_NODE_H
