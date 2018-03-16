//
// Created by jldevezas on 3/15/18.
//

#include <hgoe/edges/edge_set.h>

BOOST_CLASS_EXPORT_IMPLEMENT(EdgeSet)

bool EdgeEqual::operator()(const boost::shared_ptr<Edge> &lhs, const boost::shared_ptr<Edge> &rhs) const {
    return *lhs == *rhs && lhs->doCompare(*rhs);
}

std::size_t EdgeHash::operator()(const boost::shared_ptr<Edge> &edge) const {
    return edge->doHash();
}

bool EdgeSet::operator==(const EdgeSet &rhs) const {
    if (size() != rhs.size())
        return false;

    for (auto it = begin(), rhsIt = rhs.begin(); it != end(); it++, rhsIt++) {
        if (**it != **rhsIt)
            return false;
    }

    return true;
}

bool EdgeSet::operator!=(const EdgeSet &rhs) const {
    return !(rhs == *this);
}

/*std::size_t hash_value(const Edge &edge) {
    boost::hash<Edge::EdgeLabel> labelHasher;
    boost::hash<NodeSet> nodeSetHasher;
    std::size_t h = 0;
    boost::hash_combine(h, labelHasher(edge.label()));
    boost::hash_combine(h, nodeSetHasher(edge.getTail()));
    boost::hash_combine(h, nodeSetHasher(edge.getHead()));
    return h;
}

std::size_t hash_value(const EdgeSet &edgeSet) {
    std::size_t h = 0;
    for (const auto &edgeIt : edgeSet) {
        boost::hash_combine(h, *edgeIt);
    }
    return h;
}*/
