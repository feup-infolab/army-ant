//
// Created by jldevezas on 3/8/18.
//

#ifndef ARMY_ANT_CPP_RELATED_TO_EDGE_H
#define ARMY_ANT_CPP_RELATED_TO_EDGE_H

#include <set>
#include "edge.h"
#include "../nodes/node.h"

class RelatedToEdge : public Edge {
public:
    RelatedToEdge(std::set<Node> nodes);
};

#endif //ARMY_ANT_CPP_RELATED_TO_EDGE_H
