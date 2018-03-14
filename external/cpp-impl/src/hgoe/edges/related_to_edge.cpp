//
// Created by jldevezas on 3/8/18.
//

#include <hgoe/edges/related_to_edge.h>

BOOST_CLASS_EXPORT_IMPLEMENT(RelatedToEdge)

RelatedToEdge::RelatedToEdge() {

}

RelatedToEdge::RelatedToEdge(NodeSet nodes) : Edge(nodes) {

}

Edge::EdgeLabel RelatedToEdge::label() const {
    return EdgeLabel::RELATED_TO;
}
