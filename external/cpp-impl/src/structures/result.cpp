//
// Created by jldevezas on 3/16/18.
//

#include <structures/result.h>

#include <utility>

Result::Result() = default;

/*Result::Result(double score, boost::shared_ptr<Node> node) : score(score), node(std::move(node)) {}

Result::Result(double score, boost::shared_ptr<Node> node, const std::string &docID) : score(score), node(std::move(node)), docID(docID) {}

Result::Result(double score, boost::shared_ptr<Node> node, std::string docID, std::map<std::string, double> components)
        : score(score), node(std::move(node)), docID(std::move(docID)), components(std::move(components)) {}*/

Result::Result(double score) : score(score) {}

Result::Result(double score, const std::string &docID) : score(score), docID(docID) {}

Result::Result(double score, std::string docID, std::map<std::string, double> components)
        : score(score), docID(std::move(docID)), components(std::move(components)) {}

bool Result::operator<(const Result &rhs) const {
    return score < rhs.score;
}

bool Result::operator>(const Result &rhs) const {
    return rhs < *this;
}

bool Result::operator<=(const Result &rhs) const {
    return !(rhs < *this);
}

bool Result::operator>=(const Result &rhs) const {
    return !(*this < rhs);
}

double Result::getScore() const {
    return score;
}

void Result::setScore(double score) {
    Result::score = score;
}

/*boost::shared_ptr<Node> Result::getNode() const {
    return node;
}

void Result::setNode(boost::shared_ptr<Node> node) {
    Result::node = node;
}*/

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

std::ostream &operator<<(std::ostream &os, const Result &result) {
    /*os << "{ score: " << result.score << ", docID: " << result.docID << ", node: " << *result.node << ", |components|: "
       << result.components.size() << " }";*/
    os << "{ score: " << result.score << ", docID: " << result.docID << ", |components|: "
       << result.components.size() << " }";
    return os;
}
