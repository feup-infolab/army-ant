//
// Created by jldevezas on 3/8/18.
//

#include <structures/entity.h>

Entity::Entity(std::string label, std::string uri) {
    this->label = label;
    this->uri = uri;
}

const std::string &Entity::getLabel() const {
    return label;
}

void Entity::setLabel(const std::string &label) {
    Entity::label = label;
}

const std::string &Entity::getUri() const {
    return uri;
}

void Entity::setUri(const std::string &uri) {
    Entity::uri = uri;
}