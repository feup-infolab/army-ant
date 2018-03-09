//
// Created by jldevezas on 3/8/18.
//

#ifndef ARMY_ANT_CPP_TERM_NODE_H
#define ARMY_ANT_CPP_TERM_NODE_H

#include <string>
#include <hgoe/nodes/node.h>
#include <boost/serialization/base_object.hpp>
#include <boost/serialization/export.hpp>

class TermNode : public Node {
private:
    friend class boost::serialization::access;

    template<class Archive>
    void serialize(Archive &ar, unsigned int version) {
        ar & boost::serialization::base_object<Node>(*this);
    };
public:
    TermNode();

    explicit TermNode(std::string name);

    NodeLabel label() override;
};

BOOST_CLASS_EXPORT_KEY(TermNode)

#endif //ARMY_ANT_CPP_TERM_NODE_H
