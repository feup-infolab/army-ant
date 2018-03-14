//
// Created by jldevezas on 3/6/18.
//

#include <hgoe/nodes/node.h>

BOOST_CLASS_EXPORT_IMPLEMENT(Node)

unsigned int Node::nextNodeID = 0;

Node::Node() {
    Node::nodeID = nextNodeID++;
}

Node::Node(std::string name) {
    Node::nodeID = nextNodeID++;
    Node::name = boost::move(name);
}

const std::string &Node::getName() const {
    return name;
}

void Node::setName(const std::string &name) {
    Node::name = name;
}

/*bool Node::operator<(const Node &rhs) const {
    if (label() > rhs.label())
        return false;

    if (name > rhs.name)
        return false;

    return label() < rhs.label() || name < rhs.name;
}

bool Node::operator>(const Node &rhs) const {
    if (label() < rhs.label())
        return false;

    if (name < rhs.name)
        return false;

    return label() > rhs.label() || name > rhs.name;
}

bool Node::operator<=(const Node &rhs) const {
    return !(rhs < *this);
}

bool Node::operator>=(const Node &rhs) const {
    return !(*this < rhs);
}*/

bool Node::operator==(const Node &rhs) const {
    return label() == rhs.label() && name == rhs.name;
}

bool Node::operator!=(const Node &rhs) const {
    return !(rhs == *this);
}

std::ostream &operator<<(std::ostream &os, const Node &node) {
    os << "{ nodeID: " << node.nodeID << ", name: " << node.name << " }";
    return os;
}

Node::NodeLabel Node::label() const {
    return NodeLabel::DEFAULT;
}

unsigned int Node::getNodeID() const {
    return nodeID;
}

void Node::setNodeID(unsigned int nodeID) {
    Node::nodeID = nodeID;
}

bool Node::NodeEqual::operator()(const boost::shared_ptr<Node> &lhs, const boost::shared_ptr<Node> &rhs) const {
    //std::cout << (*lhs) << " == " << (*rhs) << ": " << (*lhs == *rhs) << std::endl;
    return *lhs == *rhs;
}

std::size_t Node::NodeHash::operator()(const boost::shared_ptr<Node> &node) const {
    boost::hash<Node::NodeLabel> labelHash;
    boost::hash<std::string> strHash;
    size_t h = 0;
    boost::hash_combine(h, labelHash(node->label()));
    boost::hash_combine(h, strHash(node->name));
    return h;
}