# CLAIA Architecture
This document outlines the architecture of the CLAIA system. It is an evolving document that will be updated as the system develops.

## Overview
CLAIA is a modular system designed to facilitate AI agent interactions, deployments, and conversations. The architecture follows several design patterns including event-driven architecture, command pattern, and repository pattern to create a flexible and extensible system.



# CORE CONCEPTS

## Model
The model represents the core data structures and capabilities:

- **Repository/Store**: Data storage and retrieval mechanisms
- **Type/Capabilities**: Defines what models can do
- **Deployments**:
  - Default (auto scaler/local)
  - APIs
  - Local
  - Auto scale

Models:
- Take input
- Translate output into conversation & basic data
- Not memory or RAG (these are reserved for agents)



# CLAIA SYSTEM

## Core Components
CLAIA consists of several interconnected components:

- **Model**: Core AI models and their capabilities
- **Deploy**: Deployment mechanisms and infrastructure
- **Tools**: Utilities that extend functionality
- **Conversation Model**: Handles dialogue and interactions
- **Data/RAG/Memory**: Information storage and retrieval
- **Commands/Processes**: Action execution framework
- **Modules**: Pluggable components for extending functionality
- **Agent**: Different agent types and behaviors



# ARCHITECTURE

## Deployment Flow

```
                  ┌─────────────┐
                  │             │
                  │  claia      │ ◄─────┐
                  |  host 1     |       |
                  │             │       │
                  └─────┬───▲───┘       │
                        │   │           │
                        │   │           │
                        ▼   │           │
┌─────────┐       ┌─────────────┐       │
│         │       │             │       │
│  API    ├──────►│  claia      │       │
│         │       │  server     ├───────┤
└────┬────┘       │             │       │
     │            └─────┬───▲───┘       │
     │                  │   │           │
     │                  │   │           │
     │                  ▼   │           │
     │            ┌─────────────┐       │
     │            │             │       │
     │            │  claia      │       │
     │            │  host 2     ├───────┘
     │            │             │
     │            └─────────────┘
     │
     ▼
┌─────────┐
│         │
│   DB    │
│         │
└─────────┘
```

Deployment process:
- Deployer can designate groups to agents
- Deployer inspects job, looks at available agents
- Forwards model (job) to model (agent/group) for faster responses
- Process setup if no match
- If model doesn't exist, check model (or agent) requirements and job requirements
- Deploy inference agents or groups
- Idle/new agents as necessary



# CLAIA FEATURES

## Use Cases
- Library (for product integration)
- Client (end user direct CLI interaction)
- Autonomous Agent/Bot (may be a translation of the two roles above or a mix of the "agent" feature)
- ExoFox AI Service

## Pricing Tier Ideas
- Potentially Freemium model tier with rate limits
- Premium model tier with Premium rate limits & speeds
- Pay-per-usage or monthly with Premium usage cap
- Buy hours/credits vs $?

## Storage
- ExoFox AI Storage (S3 bucket/slate endpoints)
- Provided storage to store:
  - Prompts
  - Artifacts
  - History/conversations
  - Logs
  - RAG type memory

## Cost Structure
- Per job cost?
- Accessing cost?
- Premium allowances for the above?

## Features

### Modules
Allow implementation-specific "mods" to create commands or scripts that can take advantage of claia's tools. Because of the library use case where claia becomes the executor.

### Custom Conversation Framework
A platform framework to transition smoothly between various modalities & preserve conversation context.

### XML Tags
- `<Image src="..." w="..." h="..." />`
- `<File />`
- `<Memory />`
- `<Sys Prompt />`
- `<Audio src="..." />`
- `<Thought src="agent" />`
- `<Prompt src="user" />`
- `<Correction src="user" />`
- `<Response src="agent" model="gpt" />`

### Hive
Claia may spawn several child processes for distributed inference, multithreaded performance, remote model loading, agentive processes, etc.

### Hive Grouping
A hive process that can group several remote instances for resource pooling, where instances in the group can intercommunicate.

### Tools
Create tools that the agent can use for various use cases:
- Console commands
- Browser/crawler
- Long context memory DB generation
- Self love training or contextual improvement
- Model selection
- Misc: calc, count, think, time, date, weather
- Call/text?
- Artifacts

### Deployments
"Your Choice" Deployments: interact with AI using any method you prefer:
- Some machines self deploy & self optimize size for hardware resources
- Remote deploy using your accounts
- Use ExoFox AI service (default?)
- Your API

### Storage
"Your Choice" Storage: instances can stream results directly back to the initiating instance to store data locally or in memory, or you can choose Exafor AI storage or an S3 style bucket of your choosing.

### Agent
Agentive processes such as contextual model switching.



# PRODUCTION
Some features may not be suitable to production deployments

User Access Control:
- intentionally avoided in Claia due to the complex nature
- would need to be implimented for access to data stores for privacy in multiuser deployments
- tools would likely need the same user access control to avoid AI models calling tools that can't run with user data access

Database Storage:
- intentionally avoided in Claia to keep things simple, small, and modular
- some data may be better suited to pull from a database
- large ammounts of data may suffer from the file based storage design in Claia

Commands:
- commands are used for user interactivity and are better avoided for production in favor of environment variables or cli args

Agent:
- the agent functionality is the star of the show when it comes to Claia
- however, due to tight coupling the integrated agent functionality may be limited in its usefulness for production deployments
- it may be better to build an agent system outside of Claia that leverages Claia's conversation model and deployment capabilities



# PIECES
Here are the core pieces of Claia's code:
- Commands -> Commands used in Claia to initiate processes and change settings
- Models
- Deploy
- Structures (Conversation & Data)
- Storage (Data Files, Memory, RAG)
- Tools -> Functions that can be used 