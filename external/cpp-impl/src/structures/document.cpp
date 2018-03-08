//
// Created by jldevezas on 3/7/18.
//

#include <structures/document.h>

Document::Document(std::string docID, std::string entity, std::string text, std::vector<triple> triples)
        : Document(NULL, docID, entity, text, triples) {

}

Document::Document(float *score, std::string docID, std::string entity, std::string text, std::vector<triple> triples) {
    this->score = score;
    this->docID = docID;
    this->entity = entity;
    this->text = text;
    this->triples = triples;
}

float *Document::getScore() const {
    return score;
}

void Document::setScore(float *score) {
    Document::score = score;
}

const std::string &Document::getDocID() const {
    return docID;
}

void Document::setDocID(const std::string &docID) {
    Document::docID = docID;
}

const std::string &Document::getEntity() const {
    return entity;
}

void Document::setEntity(const std::string &entity) {
    Document::entity = entity;
}

const std::string &Document::getText() const {
    return text;
}

void Document::setText(const std::string &text) {
    Document::text = text;
}

const std::vector<triple> &Document::getTriples() const {
    return triples;
}

void Document::setTriples(const std::vector<triple> &triples) {
    Document::triples = triples;
}

std::ostream &operator<<(std::ostream &os, const Document &document) {
    os << "{ ";

    if (document.score != nullptr) {
        os << "score: " << *document.score << std::endl << "  ";
    }

    os << "docID: " << document.docID << std::endl
       << "  entity: " << document.entity << std::endl
       << "  text: " << document.text;

    if (!document.triples.empty()) {
        os << std::endl << "  triples: ";

        for (auto t : document.triples) {
            os << std::endl << "    (" << t.subject << ", " << t.predicate << ", " << t.object << ')';
        }
    }

    os << " }" << std::endl;

    return os;
}
