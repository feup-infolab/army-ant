//
// Created by jldevezas on 3/8/18.
//

#ifndef ARMY_ANT_CPP_ENTITY_NODE_H
#define ARMY_ANT_CPP_ENTITY_NODE_H

#include <string>

#include <boost/serialization/base_object.hpp>
#include <boost/serialization/string.hpp>
#include <boost/serialization/shared_ptr.hpp>
#include <boost/serialization/export.hpp>

#include <structures/document.h>
#include <hgoe/nodes/node.h>

class EntityNode : public Node {
private:
    friend class boost::serialization::access;

    template<class Archive>
    void serialize(Archive &ar, unsigned int version) {
        ar & boost::serialization::base_object<Node>(*this);
        ar & docID;
    };

    std::string docID;
public:
    EntityNode();

    explicit EntityNode(std::string name);

    EntityNode(Document *document, std::string name);

    void print(std::ostream &os) const override;

    Label label() const override;

    void setDocID(const std::string &docID);

    std::string getDocID() const;

    bool hasDocID();
};

BOOST_CLASS_EXPORT_KEY(EntityNode)

#endif //ARMY_ANT_CPP_ENTITY_NODE_H
