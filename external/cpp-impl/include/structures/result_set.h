//
// Created by jldevezas on 3/16/18.
//

#ifndef ARMY_ANT_CPP_RESULT_SET_H
#define ARMY_ANT_CPP_RESULT_SET_H

#include <boost/container/set.hpp>
#include <boost/container/map.hpp>
#include <boost/shared_ptr.hpp>

#include <structures/result.h>

class ResultSet {
    using results_t = boost::container::set<Result>;
private:
    results_t results;
    boost::container::map<std::string, Result> maxResultPerDocID;
    boost::shared_ptr<unsigned int> numDocs;
public:
    ResultSet();

    explicit ResultSet(const results_t &results);

    ResultSet(const results_t &results, unsigned int numDocs);

    using iterator = results_t::iterator;
    using const_iterator = results_t::const_iterator;

    iterator begin();

    iterator end();

    const_iterator begin() const;

    const_iterator end() const;

    const_iterator cbegin() const;

    const_iterator cend() const;

    const results_t &getResults() const;

    void setResults(const results_t &results);

    unsigned int getNumDocs();

    void setNumDocs(unsigned int numDocs);

    void addResult(Result result);

    void addReplaceResult(Result result);
};

#endif //ARMY_ANT_CPP_RESULT_SET_H
