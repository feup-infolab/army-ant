//
// Created by jldevezas on 3/8/18.
//

#include <hgoe/edges/contained_in_edge.h>

#include <utility>

BOOST_CLASS_EXPORT_IMPLEMENT(ContainedInEdge)

ContainedInEdge::ContainedInEdge() = default;

ContainedInEdge::ContainedInEdge(NodeSet tail, NodeSet head) : Edge(boost::move(tail), boost::move(head)) {}

Edge::EdgeLabel ContainedInEdge::label() const {
    return EdgeLabel::CONTAINED_IN;
}
