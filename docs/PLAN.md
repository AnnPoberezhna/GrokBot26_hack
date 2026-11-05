# GrokMesh — starting plan

This is the plan the project is built from. It is not the project README. The full design is in [IDEA.md](IDEA.md).

Each feature below is one commit. Check a box only in the commit that lands that feature, so `git log` reads as this list from top to bottom.

**GrokMesh** is one shared database that combines a code graph with embeddings. It updates in real time from the uncommitted work of every developer on the team. Each developer's Grok Bot queries it to detect collisions before it writes code.

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
| Intents | Structured task statements: `goal`, `produces`, `consumes`, `modifies`, `scope`. |
| Leases | Active claims of developers on symbols, with a heartbeat and a TTL. |

A **node** is a symbol: function, class, endpoint, or DB model. Each node stores:

- a stable ID (`module.Class.method`), so the node survives edits that move it,
- its signature (the contract),
- an embedding of its content,
- its owner and status (`main` or `wip:<dev>`),
- edges: `calls`, `imports`, and intent → symbol.

A **lease** is active when `now - heartbeat < ttl`. Nobody clears flags by hand. Two active leases from different developers on one symbol are a collision. A lease also stores the signature before and after the change, so the broker can tell a breaking change from a safe one.

Context stays small because agents pull from the database. No agent pushes code to other agents. Each agent receives only the matched symbols, with signature and owner.

## Grok Bot integration

Grok Bot is the agent side of GrokMesh. Judges score "depth of Grok Bot / SpaceXAI API use, tools and collaborative workflows".

| Role | Grok Bot feature | What it does |
| --- | --- | --- |
| Developer bot | MCP tools + coding agent | Calls `declare_intent` and `check_collision` before it writes code. Calls `sync_file` after each edit. |
| Mesh Bot | Shared bot, messaged like a teammate | Answers "who is working on `auth/`?". Explains each collision and the fix. |
| Routine | Automations | Scans active leases every few minutes and posts a collision digest. |
| Judge | Grok | Confirms or rejects semantic collision candidates. |

Constraints that shape the build:

- **Remote MCP only.** Grok Bot connects to MCP servers over HTTP at a public URL. The broker runs FastMCP over Streamable HTTP behind a `cloudflared` tunnel.
- **No local hooks in Grok Bot.** Its coding work runs in a cloud agent, so a local post-edit hook never fires. The bot sends changed files through `sync_file`, and the broker parses them. Local agents (Claude Code, Grok Build) call the same endpoint from their hooks.
- **No API credits.** The hackathon gives subscriptions, not API credits. Keep the judge inside the bot conversation, or use our own API key only if one is available.

## Live update pipeline

1. **Sync.** The agent sends a changed file through `sync_file`.
2. **Parse.** The broker parses the file with Python `ast` and extracts symbols, signatures and `calls` edges in one pass. Tree-sitter replaces `ast` later, so the parser also accepts code that does not compile.
3. **Lease.** The broker renews the developer's lease on each changed symbol.
4. **Re-embed.** The broker hashes each symbol and re-embeds only the symbols that changed.

## Detection cascade

Each stage runs only on the candidates from the stage before it. Stages 1–2 can block an edit. Stages 3–4 only warn.

| Stage | Collision | Detection rule |
| --- | --- | --- |
| 1. Exact | Same symbol | Another developer holds an active lease on a symbol that the intent modifies or produces. |
| 2. Graph | Broken contract | A leased symbol has a breaking signature change, and a `calls` edge leads to another developer's uncommitted code. |
| 3. Semantic | Duplication, intent conflict | A new intent is close to a symbol or an intent of another developer (BM25 + cosine). |
| 4. Judge | — | Grok confirms each candidate from stage 3, with a reason. |

Each collision comes back with a resolution: **reuse** the existing symbol, **code against a stub** of its published signature, or **escalate** to the humans.

## Stack

- **Language:** Python 3.12, `uv`.
- **Store:** SQLite with FTS5 for BM25, sqlite-vec for vectors, and an edge table for the graph.
- **Parser:** Python `ast` for the MVP, tree-sitter as a stretch.
- **Embeddings:** a local code embedding model, e.g. `jina-embeddings-v2-base-code`. Fallback: BM25 only, if the model download is too slow.
- **Broker:** FastMCP over Streamable HTTP, exposed through `cloudflared`.
- **Agent access:** MCP tools `declare_intent`, `sync_file`, `check_collision`, `get_contracts`.
- **Judge and bots:** Grok Bot.

## Order of work

Each step leaves a demo that works. If time runs out, the demo uses the last finished step.

| Cut point | What the demo shows |
| --- | --- |
| After the MCP server | Two bots declare intents. GrokMesh blocks the second bot on the same symbol. |
| After broken contract | Dev A changes a signature. Dev B's bot gets a warning that names the caller. |
| After duplication | Dev B asks for a util with a different name. GrokMesh points to Dev A's symbol. |
| After Mesh Bot | A human asks the shared bot who works on what, and gets the answer. |

## Submission rules

- [ ] The repository is private, and the judges have access.
- [ ] Each team member's AI coding session exports are committed to `/sessions` at the repository root.
- [ ] All project code lands during the sprint (18:00–21:00). Ideas and plans written earlier are allowed.

## Features

One commit per row, in this order.

| | Feature | What the commit adds | Scope |
| --- | --- | --- | --- |
| [x] | Starting plan | This document. | — |
| [x] | Store | SQLite schema: symbols per layer, edges, intents, leases. | MVP |
| [x] | Parser | `ast` extracts symbols, signatures and `calls` edges from one Python file. | MVP |
| [x] | Leases | `sync_file` parses a file, writes the developer's overlay and renews leases with a TTL. | MVP |
| [x] | Intents | `declare_intent` stores a structured intent: `goal`, `produces`, `consumes`, `modifies`, `scope`. | MVP |
| [x] | Same-symbol collision | Stage 1: an intent or a sync against another developer's active lease. | MVP |
| [x] | MCP server | FastMCP over HTTP with `declare_intent`, `sync_file`, `check_collision`, `get_contracts`. Tunnel to a public URL. | MVP |
| [ ] | Grok Bot setup | Two developer bots connected to the MCP server, with instructions to check before they code. | MVP |
| [x] | Broken contract | Stage 2: a breaking signature change plus a `calls` edge into another developer's uncommitted code. | MVP |
| [ ] | Duplication | Stage 3: BM25 + cosine search of a new intent against other developers' symbols and intents. | Stretch |
| [ ] | Judge | Stage 4: Grok confirms collision candidates and drops false positives. | Stretch |
| [ ] | Mesh Bot | A shared bot that answers "who works on what" and runs a collision digest routine. | Stretch |
| [ ] | Dashboard | Web view of active leases and collisions, with live updates. | Stretch |
| [ ] | Tree-sitter | Replace `ast`, so the parser accepts code that does not compile. | Stretch |

MCP progress: the HTTP server and seven tools are implemented and tested locally.
The public tunnel and live Grok Bot connection are still pending.

Mesh Bot progress: activity snapshots and collision digests are available through
MCP on demand. The shared Grok Bot connection and scheduled digest are still pending.
