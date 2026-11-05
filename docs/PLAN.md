# GrokMesh — starting plan

This is the plan the project is built from. It is not the project README.

Each feature below is one commit. Check a box only in the commit that lands that feature, so `git log` reads as this list from top to bottom.

**GrokMesh** is one shared database that combines a code graph with embeddings. It updates in real time from the uncommitted work of every developer on the team. Each developer's agent queries it to detect collisions before it writes code.

## Problem

- **Isolated agents.** Each developer's coding agent works in its own session.
- **Fast drift.** Agents write code fast, so parallel work drifts apart within hours: duplicate utilities, broken contracts, clashing intents.
- **Late detection.** Teams find these conflicts at the pull request.

### Why existing tools miss it

| Kind | Examples | What they miss |
| --- | --- | --- |
| Context engines | Augment, Cursor | They index uncommitted work, but only for one user. |
| Conflict prevention | GitKraken | It compares lines of text in committed branches, not meaning. |
| Agent coordination | Claude Code agent teams, MCP Agent Mail | It locks files. It does not track contracts or intents across developers. |

## Data model

| Layer | Content |
| --- | --- |
| Base | Index of the main branch. |
| Overlay per developer | Changed symbols from that developer's uncommitted work. |
| Intents | Short task statements linked to symbols, e.g. "Dev A: JWT in auth/". |

A **node** is a symbol: function, class, endpoint, or DB model. Each node stores:

- its signature (the contract),
- an embedding of its content,
- its owner and status (`main` or `wip:<dev>`),
- edges: `calls`, `imports`, `implements`, and intent → symbol.

Context stays small because agents pull from the database. No agent pushes code to other agents. Each agent receives only the matched symbols, with signature and owner.

## Live update pipeline

1. **Parse.** A post-edit hook runs tree-sitter on the changed file. Tree-sitter tolerates syntax errors, so it also parses unfinished code that does not compile.
2. **Re-embed.** The pipeline hashes each symbol and re-embeds only the symbols that changed.
3. **Publish.** The broker writes the changed nodes to the developer's overlay and sends a pub/sub event.

## Collision types

The cosine-similarity search returns the candidates. Then Grok, as the LLM judge, confirms each one to cut false positives.

| Collision | Detection rule |
| --- | --- |
| Duplication | A new intent's embedding is close to a symbol in another developer's overlay. |
| Broken contract | A signature changes, and a `calls` edge leads to another developer's uncommitted code. |
| Intent conflict | Two active intents are semantically close and target the same subgraph. |

## Stack

- **Store:** SQLite with sqlite-vec for vectors and an edge table for the graph.
- **Parser:** tree-sitter for one language.
- **Embeddings:** a local code embedding model, e.g. `jina-embeddings-v2-base-code`.
- **Judge:** Grok.
- **Agent access:** an MCP server (`publish_intent`, `check_collision`, `get_contracts`) plus agent hooks.

## Scope

- **MVP:** per-developer overlays, symbol embeddings, duplication detection.
- **Stretch:** `calls` edges and broken-contract detection. This has the strongest demo impact.
- **Main risks:** false positives in semantic matching, and the privacy of uncommitted work. The fixes are the LLM judge, and publishing that each developer opts into per module.

## Features

One commit per row. MVP first, then stretch.

| | Feature | What the commit adds | Scope |
| --- | --- | --- | --- |
| [x] | Starting plan | This document. | — |
| [ ] | Store | SQLite schema: base index, per-developer overlay, intents, edges, sqlite-vec. | MVP |
| [ ] | Parser | Post-edit hook. Tree-sitter extracts symbols from one language, including code that does not compile. | MVP |
| [ ] | Embeddings | Hash each symbol. Re-embed only the symbols that changed. | MVP |
| [ ] | Publish | Write changed nodes to that developer's overlay and emit a pub/sub event. | MVP |
| [ ] | Duplication | Cosine search: a new intent against symbols in other developers' overlays. | MVP |
| [ ] | MCP server | `publish_intent`, `check_collision`, `get_contracts`. Agents pull matched symbols only. | MVP |
| [ ] | Call graph | `calls` edges between symbols. | Stretch |
| [ ] | Broken contract | A changed signature plus a `calls` edge into another developer's uncommitted code. | Stretch |
| [ ] | Intent conflict | Two active intents, semantically close, on the same subgraph. | Stretch |
| [ ] | Judge | Grok confirms collision candidates and drops false positives. | Stretch |
