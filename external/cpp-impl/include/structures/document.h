//
// Created by jldevezas on 3/7/18.
//

#ifndef ARMY_ANT_CPP_DOCUMENT_H
#define ARMY_ANT_CPP_DOCUMENT_H

#include <string>
#include <tuple>
#include <vector>

typedef std::tuple <std::string, std::string, std::string> triple;

class Document {
private:
    float *score;
    std::string docID;
    std::string title;
    std::string text;
    std::vector <triple> triples;
public:
    Document(std::string docID, std::string title, std::string text, std::vector <triple> triples);

    Document(float *score, std::string docID, std::string title, std::string text, std::vector <triple> triples);
};

#endif //ARMY_ANT_CPP_DOCUMENT_H
