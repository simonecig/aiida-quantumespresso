# `aiida-quantumespresso`
This is a fork of the official AiiDA plugin for [Quantum ESPRESSO](https://www.quantum-espresso.org/) which adds support for the new version of pw4gww.x and its new parallelisation capabilities. 
In particular, the following Calculations have been added:
- Pw4gwwCalculation
- EasyAnalyserCalculation

with the related parsers:
- Pw4gwwParser
- EasyAnalyserParser

In addition, the plugin also provides the following new workchains:
- Pw4gwwWorkChain
- Pw4gwwClusterWorkChain

## Installation
To install from source:

    git clone https://github.com/aiidateam/aiida-quantumespresso
    pip install aiida-quantumespresso
