//
// Created by jldevezas on 3/15/18.
//

#include <hgoe/nodes/node_set.h>

BOOST_CLASS_EXPORT_IMPLEMENT(NodeSet)

bool NodeSet::operator==(const NodeSet &rhs) const {
    if (size() != rhs.size())
        return false;

    for (auto it = begin(), rhsIt = rhs.begin(); it != end(); it++, rhsIt++) {
        if (**it != **rhsIt)
            return false;
    }

    return true;
}

bool NodeSet::operator!=(const NodeSet &rhs) const {
    return !(rhs == *this);
}

std::ostream &operator<<(std::ostream &os, const NodeSet &nodeSet) {
    os << "{ ";
    bool first = true;
    for (const auto &nodeIt : nodeSet) {
        if (first)
            first = false;
        else
            os << ", ";
        os << *nodeIt;
    }
    os << " }";
    return os;
}

std::size_t hash_value(const Node &node) {
    boost::hash<Node::NodeLabel> labelHash;
    boost::hash<std::string> strHash;
    size_t h = 0;
    boost::hash_combine(h, labelHash(node.label()));
    boost::hash_combine(h, strHash(node.getName()));
    return h;
}

std::size_t hash_value(const NodeSet &nodeSet) {
    std::size_t h = 0;
    for (const auto &nodeIt : nodeSet) {
        boost::hash_combine(h, *nodeIt);
    }
    return h;
}
