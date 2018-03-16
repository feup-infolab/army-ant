//
// Created by jldevezas on 3/15/18.
//

#include <hgoe/nodes/node_set.h>
#include <hgoe/nodes/node.h>

BOOST_CLASS_EXPORT_IMPLEMENT(NodeSet)

bool NodeEqual::operator()(const boost::shared_ptr<Node> &lhs, const boost::shared_ptr<Node> &rhs) const {
    return *lhs == *rhs;
}

std::size_t NodeHash::operator()(const boost::shared_ptr<Node> &node) const {
    boost::hash<Node::Label> labelHash;
    boost::hash<std::string> strHash;
    size_t h = 0;
    boost::hash_combine(h, labelHash(node->label()));
    boost::hash_combine(h, strHash(node->getName()));
    return h;
}

bool NodeSet::operator==(const NodeSet &rhs) const {
    if (size() != rhs.size())
        return false;

    for (auto it = this->begin(); it != this->end(); it++) {
        if (rhs.find(*it) == rhs.end())
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

std::size_t hash_value(const NodeSet &nodeSet) {
    std::size_t h = 0;
    for (const auto &nodeIt : nodeSet) {
        //boost::hash_combine(h, *nodeIt);
        h ^= hash_value(*nodeIt); // since order matters in hash_combine!
    }
    return h;
}