//
// Created by jldevezas on 3/7/18.
//

#ifndef ARMY_ANT_CPP_DOCUMENT_H
#define ARMY_ANT_CPP_DOCUMENT_H

#include <string>
#include <tuple>
#include <vector>
#include <ostream>

typedef struct {
    std::string subject;
    std::string predicate;
    std::string object;
} Triple;

class Document {
private:
    float *score;
    std::string docID;
    std::string entity;
    std::string text;
    std::vector <Triple> triples;
public:
    Document(std::string docID, std::string entity, std::string text, std::vector <Triple> triples);

    Document(float *score, std::string docID, std::string entity, std::string text, std::vector <Triple> triples);

    float *getScore() const;

    void setScore(float *score);

    const std::string &getDocID() const;

    void setDocID(const std::string &docID);

    const std::string &getEntity() const;

    void setEntity(const std::string &entity);

    const std::string &getText() const;

    void setText(const std::string &text);

    const std::vector<Triple> &getTriples() const;

    void setTriples(const std::vector<Triple> &triples);

    friend std::ostream &operator<<(std::ostream &os, const Document &document);
};

#endif //ARMY_ANT_CPP_DOCUMENT_H
