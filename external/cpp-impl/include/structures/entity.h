//
// Created by jldevezas on 3/8/18.
//

#ifndef ARMY_ANT_CPP_ENTITY_H
#define ARMY_ANT_CPP_ENTITY_H

#include <string>

class Entity {
private:
    std::string label;
    std::string uri;
public:
    Entity(std::string label, std::string uri);

    const std::string &getLabel() const;

    void setLabel(const std::string &label);

    const std::string &getUri() const;

    void setUri(const std::string &uri);
};

#endif //ARMY_ANT_CPP_ENTITY_H
