//
// Created by jldevezas on 3/7/18.
//

#ifndef ARMY_ANT_CPP_ENGINE_H
#define ARMY_ANT_CPP_ENGINE_H

#include <string>
#include <vector>

#include <boost/log/core.hpp>
#include <boost/log/trivial.hpp>
#include <boost/log/expressions.hpp>

#include <structures/document.h>
#include <structures/result_set.h>

namespace logging = boost::log;

class Engine {
public:
    Engine() {
        logging::core::get()->set_filter(logging::trivial::severity >= logging::trivial::trace);
    };

    virtual void index(Document document) = 0;

    virtual ResultSet search(std::string query, unsigned int offset, unsigned int limit) = 0;

    virtual void postProcessing() {};

    virtual void inspect(std::string feature) {};

    virtual void close() {};

    std::vector<std::string> analyze(std::string text);
};

#endif //ARMY_ANT_CPP_ENGINE_H
