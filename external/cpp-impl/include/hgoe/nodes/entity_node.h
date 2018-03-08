//
// Created by jldevezas on 3/8/18.
//

#ifndef ARMY_ANT_CPP_ENTITY_NODE_H
#define ARMY_ANT_CPP_ENTITY_NODE_H

#include <structures/document.h>
#include "node.h"

class EntityNode : public Node {
private:
    Document *document;
public:
    EntityNode(std::string name);

    EntityNode(Document *document, std::string name);
};

#endif //ARMY_ANT_CPP_ENTITY_NODE_H
