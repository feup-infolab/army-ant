//
// Created by jldevezas on 3/16/18.
//

#include <structures/result.h>

Result::Result(double score, Node *node) : score(score), node(node) {}

Result::Result(double score, Node *node, const std::string &docID) : score(score), node(node), docID(docID) {}

Result::Result(double score, Node *node, const std::string &docID, const std::map<std::string, double> &components)
        : score(score), node(node), docID(docID), components(components) {}

double Result::getScore() const {
    return score;
}

void Result::setScore(double score) {
    Result::score = score;
}

Node *Result::getNode() const {
    return node;
}

void Result::setNode(Node *node) {
    Result::node = node;
}

const std::string &Result::getDocID() const {
    return docID;
}

void Result::setDocID(const std::string &docID) {
    Result::docID = docID;
}

const std::map<std::string, double> &Result::getComponents() const {
    return components;
}

void Result::setComponents(const std::map<std::string, double> &components) {
    Result::components = components;
}

const double &Result::getComponent(std::string key) const {
    return this->components.at(key);
}

void Result::setComponent(const std::string &key, const double &value) {
    this->components[key] = value;
}

void Result::unsetComponent(const std::string &key) {
    this->components.erase(key);
}
