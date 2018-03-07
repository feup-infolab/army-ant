//
// Created by jldevezas on 3/7/18.
//

#include <engine.h>
#include <boost/algorithm/string.hpp>
#include <boost/tokenizer.hpp>

std::vector<std::string> Engine::analyze(std::string text) {
    std::vector<std::string> tokens = std::vector<std::string>();

    boost::algorithm::to_lower(text);
    boost::tokenizer<> tok(text);
    for (const auto &token : tok) {
        tokens.push_back(token);
    }

    return tokens;
}
