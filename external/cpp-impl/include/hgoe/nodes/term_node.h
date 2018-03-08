//
// Created by jldevezas on 3/8/18.
//

#ifndef ARMY_ANT_CPP_TERM_NODE_H
#define ARMY_ANT_CPP_TERM_NODE_H

#include <string>
#include "node.h"

class TermNode : public Node {
public:
    TermNode(std::string name);

    NodeLabel label() override;
};

#endif //ARMY_ANT_CPP_TERM_NODE_H
