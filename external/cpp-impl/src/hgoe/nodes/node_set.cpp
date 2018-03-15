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