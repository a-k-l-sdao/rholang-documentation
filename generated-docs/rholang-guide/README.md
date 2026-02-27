# Rholang Developer Guide

Rholang is a concurrent, process-oriented programming language for the F1R3FLY blockchain. Everything is a process communicating over channels. There is no shared mutable state -- processes exchange data by sending and receiving messages.

This guide covers the language from basics to system contracts.

## Contents

1. [Language Basics](./01-language-basics.md) -- Syntax, data types, channels, processes
2. [Contracts and Patterns](./02-contracts-and-patterns.md) -- Contracts, pattern matching, state
3. [System Contracts](./03-system-contracts.md) -- rho:io, rho:crypto, rho:registry, vaults, AI
4. [Deploys and the Registry](./04-deploys-and-registry.md) -- How to deploy, exploratory vs full, registry URIs
5. [Security Patterns](./05-security-patterns.md) -- Bundles, capabilities, attenuation, revocation
6. [Standard Library](./06-standard-library.md) -- ListOps, TreeHashMap, NonNegativeNumber, MakeMint, AuthKey
7. [Examples](./07-examples.md) -- Complete working examples
