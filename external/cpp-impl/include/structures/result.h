//
// Created by jldevezas on 3/16/18.
//

#ifndef ARMY_ANT_CPP_RESULT_H
#define ARMY_ANT_CPP_RESULT_H

#include <hgoe/nodes/node.h>
#include <ostream>

class Result {
private:
    double score;
    boost::shared_ptr<Node> node;
    std::string docID;
    std::map<std::string, double> components;
public:
    Result();

    /*Result(double score, boost::shared_ptr<Node> node);

    Result(double score, boost::shared_ptr<Node> node, const std::string &docID);

    Result(double score, boost::shared_ptr<Node> node, std::string docID, std::map<std::string, double> components);*/

    Result(double score);

    Result(double score, const std::string &docID);

    Result(double score, std::string docID, std::map<std::string, double> components);

    bool operator<(const Result &rhs) const;

    bool operator>(const Result &rhs) const;

    bool operator<=(const Result &rhs) const;

    bool operator>=(const Result &rhs) const;

    friend std::ostream &operator<<(std::ostream &os, const Result &result);

    double getScore() const;

    void setScore(double score);

    /*boost::shared_ptr<Node> getNode() const;

    void setNode(boost::shared_ptr<Node> node);*/

    const std::string &getDocID() const;

    void setDocID(const std::string &docID);

    const std::map<std::string, double> &getComponents() const;

    void setComponents(const std::map<std::string, double> &components);

    const double &getComponent(std::string key) const;

    void setComponent(const std::string &key, const double &value);

    void unsetComponent(const std::string &key);
};

#endif //ARMY_ANT_CPP_RESULT_H
