//
// Created by jldevezas on 3/8/18.
//

#ifndef ARMY_ANT_CPP_CONTAINED_IN_EDGE_H
#define ARMY_ANT_CPP_CONTAINED_IN_EDGE_H

#include "edge.h"

class ContainedInEdge : public Edge {
public:
    ContainedInEdge(std::set<Node> tail, std::set<Node> head);
};

#endif //ARMY_ANT_CPP_CONTAINED_IN_EDGE_H
