//
// Created by jldevezas on 3/6/18.
//

#include "hypergraph_of_entity.h"

#include <iostream>

#include <boost/shared_ptr.hpp>
#include <Hypergraph/model/Hypergraphe.hh>
#include <Hypergraph/model/HyperFactory.hh>
#include <Hypergraph/model/MotorAlgorithm.hh>
#include <Hypergraph/algorithm/Isomorph.hh>
#include <Hypergraph/algorithm/Simple.hh>

int HypergraphOfEntity::test() {
    // Creating the hypergraph inside smart pointer
    boost::shared_ptr<HypergrapheAbstrait> ptrHpg( new Hypergraphe() );

    // Starting the create session
    HyperFactory::startSession(ptrHpg);

    // Creating the hyper-edges
    boost::shared_ptr<HyperEdge> ptrEdge1 ( HyperFactory::newHyperEdge() );
    boost::shared_ptr<HyperEdge> ptrEdge2 ( HyperFactory::newHyperEdge() );

    // Creating the hyper-vertexes
    boost::shared_ptr<HyperVertex> ptrVertexA( HyperFactory::newHyperVertex() );
    boost::shared_ptr<HyperVertex> ptrVertexB( HyperFactory::newHyperVertex() );

    // The hyper-vertex A is contained inside the hyper-edge 1
    HyperFactory::link(ptrVertexA, ptrEdge1);
    // The hyper-vertex B is contained inside the hyper-edge 2
    HyperFactory::link(ptrVertexB, ptrEdge2);

    // Adding the hyper-vertexes in the hypergraph
    ptrHpg->addHyperVertex( ptrVertexA );
    ptrHpg->addHyperVertex( ptrVertexB );

    // Adding the hyper-edges in the hypergraph
    ptrHpg->addHyperEdge(ptrEdge1);
    ptrHpg->addHyperEdge(ptrEdge2);

    // Creating the adjacent matrix inside the hypergraph
    ptrHpg->flush();

    // Closing the session
    HyperFactory::closeSession();


    // -- -- --


    // Initializing the Isomorphism algorithm with ptrHpg (twice, just for the example)
    boost::shared_ptr<AlgorithmeAbstrait> isomorphPtr( new Isomorph( ptrHpg , ptrHpg ) );

    // Setting the motor's algorithm
    MotorAlgorithm::setAlgorithme( isomorphPtr );

    // Running the motor
    MotorAlgorithm::runAlgorithme();

    // Getting the result
    RStructure r1( isomorphPtr->getResult() );

    if( r1.getBooleanResult() ) {
        std::cout << "The hypergraph is isomorph with itself" << std::endl;
    }

    // -- -- --

    // Initializing the Simple algorithm with ptrHpg (twice, just for the example)
    boost::shared_ptr<AlgorithmeAbstrait> simplephPtr( new Simple( ptrHpg ) );

    // Setting the motor's algorithm
    MotorAlgorithm::setAlgorithme( simplephPtr );

    // Running the motor
    MotorAlgorithm::runAlgorithme();

    // Getting the result
    RStructure r2( simplephPtr->getResult() );

    if( r2.getBooleanResult() ) {
        std::cout << "The hypergraph is simple." << std::endl;
    }

    return 0;
}