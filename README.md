# Multi-Agent-Code-Refactor

**Multi-Agent-Code-Refactor** is a local, microservices-based system designed to optimize code files. Each agent in the system is specialized for a specific aspect of code improvement, including performance enhancement, architecture improvements, and adherence to coding style guidelines. By distributing responsibilities across multiple components, the system can analyze and refactor large codebases efficiently.


## Architecture

```mermaid
flowchart TD
    User(["📁 Code Input"]):::input --> Orch

    subgraph Docker Network
        Orch["🧠 Orchestrator"]
        Redis[("⚡ Redis\nMessage Broker")]
        Perf["🚀 Performance Agent"]
        Arch["🏗️ Architecture Agent"]
        Style["✨ Style Agent"]
    end

    Orch -->|"publish task"| Redis
    Redis -->|"subscribe"| Perf
    Redis -->|"subscribe"| Arch
    Redis -->|"subscribe"| Style
    Perf -->|"publish result"| Redis
    Arch -->|"publish result"| Redis
    Style -->|"publish result"| Redis
    Redis -->|"collect & merge"| Orch
    Orch --> Out(["📝 Refactored Code"]):::output

    classDef input fill:#1e293b,stroke:#3b82f6,color:#93c5fd
    classDef output fill:#1e293b,stroke:#22c55e,color:#86efac
```

**Stack:** Python · Redis · Docker