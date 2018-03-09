//
// Created by jldevezas on 3/8/18.
//

#include <hgoe/edges/related_to_edge.h>

BOOST_CLASS_EXPORT_IMPLEMENT(RelatedToEdge)

RelatedToEdge::RelatedToEdge() {

}

RelatedToEdge::RelatedToEdge(std::set<Node *> nodes) : Edge(nodes) {

}