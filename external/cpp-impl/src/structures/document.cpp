//
// Created by jldevezas on 3/7/18.
//

#include <structures/document.h>

#include <utility>

Document::Document(std::string docID, std::string entity, std::string text, std::vector<Triple> triples)
        : Document(nullptr, std::move(docID), std::move(entity), std::move(text), std::move(triples)) {

}

Document::Document(float *score, std::string docID, std::string entity, std::string text, std::vector<Triple> triples) {
    this->score = score;
    this->docID = std::move(docID);
    this->title = std::move(entity);
    this->text = std::move(text);
    this->triples = std::move(triples);
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

const std::string &Document::getTitle() const {
    return title;
}

void Document::setTitle(const std::string &title) {
    Document::title = title;
}

const std::string &Document::getText() const {
    return text;
}

void Document::setText(const std::string &text) {
    Document::text = text;
}

const std::vector<Triple> &Document::getTriples() const {
    return triples;
}

void Document::setTriples(const std::vector<Triple> &triples) {
    Document::triples = triples;
}

std::ostream &operator<<(std::ostream &os, const Document &document) {
    os << "{ ";

    if (document.score != nullptr) {
        os << "score: " << *document.score << std::endl << "  ";
    }

    os << "docID: " << document.docID << std::endl
       << "  title: " << document.title << std::endl
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
