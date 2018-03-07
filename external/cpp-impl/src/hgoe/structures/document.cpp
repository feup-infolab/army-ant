//
// Created by jldevezas on 3/7/18.
//

#include <structures/document.h>

Document::Document(std::string docID, std::string title, std::string text, std::vector<triple> triples)
        : Document(NULL, docID, title, text, triples) {

}

Document::Document(float *score, std::string docID, std::string title, std::string text, std::vector<triple> triples) {
    *this->score = *score;
    this->docID = docID;
    this->title = title;
    this->text = text;
    this->triples = triples;
}
