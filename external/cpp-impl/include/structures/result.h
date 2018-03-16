//
// Created by jldevezas on 3/16/18.
//

#ifndef ARMY_ANT_CPP_RESULT_H
#define ARMY_ANT_CPP_RESULT_H

#include <hgoe/nodes/node.h>

class Result {
private:
    double score;
    Node *node;
    std::string docID;
    std::map<std::string, double> components;
public:
    Result(double score, Node *node);

    Result(double score, Node *node, const std::string &docID);

    Result(double score, Node *node, const std::string &docID, const std::map<std::string, double> &components);

    double getScore() const;

    void setScore(double score);

    Node *getNode() const;

    void setNode(Node *node);

    const std::string &getDocID() const;

    void setDocID(const std::string &docID);

    const std::map<std::string, double> &getComponents() const;

    void setComponents(const std::map<std::string, double> &components);

    const double &getComponent(std::string key) const;

    void setComponent(const std::string &key, const double &value);

    void unsetComponent(const std::string &key);
};

#endif //ARMY_ANT_CPP_RESULT_H
