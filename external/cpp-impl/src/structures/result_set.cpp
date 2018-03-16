//
// Created by jldevezas on 3/16/18.
//

#include <structures/result_set.h>

ResultSet::ResultSet(const ResultSet::results_t &results) : results(results), numDocs(nullptr) {}

ResultSet::ResultSet(const ResultSet::results_t &results, unsigned int numDocs) : results(results), numDocs(&numDocs) {}

ResultSet::iterator ResultSet::begin() {
    return results.begin();
}

ResultSet::iterator ResultSet::end() {
    return results.end();
}

ResultSet::const_iterator ResultSet::begin() const {
    return results.begin();
}

ResultSet::const_iterator ResultSet::end() const {
    return results.end();
}

ResultSet::const_iterator ResultSet::cbegin() const {
    return results.cbegin();
}

ResultSet::const_iterator ResultSet::cend() const {
    return results.cend();
}

const ResultSet::results_t &ResultSet::getResults() const {
    return results;
}

void ResultSet::setResults(const ResultSet::results_t &results) {
    ResultSet::results = results;
}

unsigned int ResultSet::getNumDocs() const {
    if (numDocs == nullptr) {
        numDocs = boost::make_shared<unsigned int>(results.size());
    }
    return *numDocs;
}

void ResultSet::setNumDocs(const unsigned int numDocs) {
    ResultSet::numDocs = boost::make_shared<unsigned int>(numDocs);
}

void ResultSet::addResult(Result result) {
    results.insert(result);
}

void ResultSet::addReplaceResult(Result result) {
    maxResultPerDocID[result.getDocID()] = result;
    results.insert(result);

    auto maxResult = maxResultPerDocID.find(result.getDocID());
    if (maxResult != maxResultPerDocID.end() && result.getScore() > (*maxResult)->getScore()) {
        results.erase(maxResult);
    }
}