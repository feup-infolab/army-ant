//
// Created by jldevezas on 3/8/18.
//

#include <hgoe/edges/contained_in_edge.h>

#include <utility>

BOOST_CLASS_EXPORT_IMPLEMENT(ContainedInEdge)

ContainedInEdge::ContainedInEdge() = default;

ContainedInEdge::ContainedInEdge(std::set<Node *, NodeComp> tail, std::set<Node *, NodeComp> head) :
        Edge(std::move(tail), std::move(head)) {}