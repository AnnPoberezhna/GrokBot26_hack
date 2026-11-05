# GrokMesh — Source Idea

> **Status:** source idea, version 1 (2026-11-05)
> **One-liner:** GrokMesh is one shared database that combines a code graph with embeddings. It updates in real time from the uncommitted work of every developer on the team. Each developer's coding agent queries it to detect collisions before it writes code.

---

## 0. Problem

- **Isolated agents:** Each developer's coding agent works in its own session.
- **Fast drift:** Agents write code about 20× faster than people, so parallel work drifts apart within hours: duplicate utilities, broken contracts, clashing intents.
- **Late detection:** Teams find these conflicts at the pull request, after the code already exists.

### Why existing tools miss it

| Tool | What it does | Limit |
|---|---|---|
| Augment, Cursor | Index uncommitted work for semantic search. | Each index serves one user only. |
| GitKraken Conflict Prevention | Warns before merge about overlapping edits in teammates' committed, unmerged branches. | Compares lines of text, not meaning. Does not see uncommitted work. |
| Claude Code agent teams, MCP Agent Mail | Give agents messaging, shared task lists and advisory file locks. | Lock files, not contracts or intents. Coordinate the agents of one developer or one orchestrator. |
| MCP / A2A protocols | Connect agents to tools or to other agents. | No shared team state. |

**Positioning:** Contract-first, intent-level synchronization across the coding agents of different developers, with semantic leases on symbols.

---

## 1. Review of the first design

| Component | Problem | Fix |
|---|---|---|
| Free-text intents | Cosine similarity on free text is noisy. It produces false positives. | **Structured intents:** an LLM converts each prompt into fields: `produces`, `consumes`, `modifies`, `scope`. |
| Node identity | Tree-sitter node positions change after edits, renames and moves. | **Stable symbol IDs** in SCIP format (`pkg/module/Class#method().`), plus a hash of the body to detect renames. |
| `touched: bool` | The flag goes stale when a developer abandons work. | **Leases with heartbeat and TTL**, the pattern that etcd and Kubernetes use. |
| Shared mutable state | Many agents write to one store. Writes can race and corrupt state. | **Event sourcing, one writer per overlay.** Each developer appends events only to their own log. The broker builds the current state from the logs. No CRDT is necessary. |
| Contract changes | The design does not separate breaking changes from safe ones. | **API diff classification:** Griffe for Python, API Extractor for TypeScript. A new optional parameter is safe. A removed parameter is breaking. |
| Detection | One similarity threshold for everything. | **Detection cascade:** cheap exact checks first, the LLM last. |
| Output | Detection only. The agent still has to decide what to do. | **Resolution protocol:** reuse, code against a stub, negotiate, or escalate to a human. |
| Branches | Overlays assume that everyone works on top of `main`. | Compute each overlay against the developer's **merge-base**. Fold the overlay into the base on merge. |

---

## 2. Architecture

```
 Dev A machine                     Broker                       Dev B machine
┌──────────────────┐      ┌──────────────────────────┐      ┌──────────────────┐
│ Agent + hooks    │      │ Event log (append-only)  │      │ Agent + hooks    │
│ tree-sitter      │─evt─▶│ Projections:             │◀─evt─│ tree-sitter      │
│ local embeddings │      │  - symbol graph (base)   │      │ local embeddings │
│ (stays local)    │◀─msg─│  - overlays per dev      │─msg─▶│ (stays local)    │
└──────────────────┘      │  - leases, intents       │      └──────────────────┘
                          │ Detection cascade        │
                          │ Resolution router        │
                          │ MCP server + dashboard   │
                          └──────────────────────────┘
```

### Layers

| Layer | Content |
|---|---|
| **Base** | Index of the `main` branch |
| **Overlay per developer** | Changed symbols from that developer's uncommitted work, relative to their merge-base |
| **Intents** | Structured task statements linked to symbols |
| **Leases** | Active claims of developers on symbols, with TTL |

**Local-first privacy:** Each developer's machine parses code and computes embeddings. Only signatures, embeddings and one-line summaries leave the machine. Source code never leaves.

**Pull, not push:** Agents query the broker. No agent pushes code to other agents. Each agent receives only the matched symbols, with signature and owner. Context windows stay small.

---

## 3. Data model

```sql
-- Symbols: base layer plus per-developer overlays
CREATE TABLE symbol (
    symbol_id   TEXT NOT NULL,        -- SCIP-style stable ID
    layer       TEXT NOT NULL,        -- 'base' or 'wip:<dev_id>'
    kind        TEXT NOT NULL,        -- function | class | endpoint | model
    signature   TEXT NOT NULL,
    body_hash   TEXT NOT NULL,
    summary     TEXT,                 -- one sentence, LLM-generated
    PRIMARY KEY (symbol_id, layer)
);
CREATE VIRTUAL TABLE symbol_vec USING vec0(embedding float[768]);   -- sqlite-vec
CREATE VIRTUAL TABLE symbol_fts USING fts5(symbol_id, signature, summary);

CREATE TABLE edge (
    src   TEXT NOT NULL,
    dst   TEXT NOT NULL,
    kind  TEXT NOT NULL,              -- calls | imports | implements
    layer TEXT NOT NULL
);

-- Structured intents
CREATE TABLE intent (
    intent_id  TEXT PRIMARY KEY,
    dev_id     TEXT NOT NULL,
    goal       TEXT NOT NULL,         -- "Issue JWT tokens"
    produces   JSON NOT NULL,         -- symbols that the intent will create
    consumes   JSON NOT NULL,         -- symbols that the intent depends on
    modifies   JSON NOT NULL,         -- existing symbols that the intent changes
    scope      JSON NOT NULL,         -- path globs
    status     TEXT NOT NULL          -- active | done | abandoned
);

-- Semantic leases on symbols
CREATE TABLE lease (
    symbol_id   TEXT NOT NULL,
    dev_id      TEXT NOT NULL,
    intent_id   TEXT,
    mode        TEXT NOT NULL,        -- read | write
    heartbeat   INTEGER NOT NULL,     -- unix ts, renewed on every edit
    ttl_s       INTEGER NOT NULL DEFAULT 1800,
    sig_before  TEXT,                 -- signature in base
    sig_after   TEXT,                 -- signature in overlay
    change_kind TEXT,                 -- none | compatible | breaking
    PRIMARY KEY (symbol_id, dev_id)
);
```

A lease is **active** when `now - heartbeat < ttl_s`. Nobody clears flags by hand. Two active write leases on one symbol are a collision.

---

## 4. Event protocol

Each developer appends events only to their own log. The broker replays all logs to build the current state.

| Event | Trigger |
|---|---|
| `IntentDeclared` | Prompt submit hook |
| `SymbolTouched` | Post-edit hook (it also renews the lease heartbeat) |
| `SignatureChanged` | Post-edit hook, when the API diff is not empty |
| `IntentClosed` | Task done, or the agent session ends |
| `OverlayMerged` | Git post-merge hook (the overlay folds into the base) |
| `ResolutionChosen` | An agent or a human picks a resolution |

### Live update pipeline

1. **Parse:** A post-edit hook runs tree-sitter on the changed file. Tree-sitter tolerates syntax errors, so it also parses unfinished code that does not compile.
2. **Re-embed:** The indexer hashes each symbol and re-embeds only the symbols that changed.
3. **Publish:** The indexer emits events. The broker updates the developer's overlay and notifies subscribers.

---

## 5. Detection cascade

Each stage runs only on the candidates from the stage before it. This keeps latency and cost low.

| Stage | Method | Cost | Catches |
|---|---|---|---|
| 1. Exact | Intersect the new intent's `modifies`/`produces` with active write leases | < 1 ms | Same-symbol edits |
| 2. Graph | 1-hop `calls`/`imports` from leased symbols with `change_kind = breaking` | < 5 ms | Broken contracts |
| 3. Hybrid retrieval | BM25 (FTS5) + vector (sqlite-vec), fused by Reciprocal Rank Fusion | ~20 ms | Duplicate functionality under different names |
| 4. LLM judge | Grok confirms or rejects each candidate, with a reason | ~1 s, async | False positives from stage 3 |

### Collision types

| Collision | Detection rule | Severity |
|---|---|---|
| **Same symbol** | Another developer holds a write lease on the target symbol. | Conflict (block) |
| **Broken contract** | A leased symbol has a breaking signature change, and a `calls` edge leads to the agent's code. | Conflict (block) |
| **Reverse dependency** | Another developer edits a symbol that calls the agent's target symbol. | Warning |
| **Duplication** | A new intent is semantically close to a symbol in another developer's overlay. | Warning |
| **Intent conflict** | Two active intents are semantically close and target the same subgraph. | Warning |

**Latency budget:** The pre-edit hook runs only stages 1–2, so edits stay fast. Stages 3–4 run at prompt submit, before the agent starts to write code.

---

## 6. Resolution protocol

GrokMesh does more than detect a collision. It gives the agent concrete next actions.

| Resolution | When | Effect |
|---|---|---|
| **Reuse** | Another developer already produces the same symbol. | The agent imports the existing symbol. |
| **Code against stub** | The other symbol is still in progress, but its signature is published. | The broker generates a typed stub from that signature. The agent codes against it, so the collision becomes a dependency. |
| **Negotiate** | Two intents modify the same contract. | One agent sends a contract proposal to the other agent. The owner accepts or counters it. |
| **Escalate** | Negotiation fails, or the change is breaking. | Both humans get a notification with a diff of the two signatures. |

**Main differentiator: code against stub.** Parallel work on dependent code becomes safe. Developer B does not have to wait for Developer A to finish.

### Example message in the agent's context

```
CONFLICT: auth.hash_token() is active (Dev A, 4 min ago).
Change: signature (token: str) -> (token: str, salt: bytes)  [breaking]
Intent: "JWT issuance in auth/".
Options: reuse | code against stub | negotiate | escalate
```

---

## 7. Agent integration

| Hook | Action |
|---|---|
| `UserPromptSubmit` | Extract a structured intent → run stages 1–4 → inject the result into context. |
| `PreToolUse` (Edit/Write) | Map file + line range to symbols → run stages 1–2 → allow, warn, or block with a reason. |
| `PostToolUse` (Edit/Write) | Parse → re-embed changed symbols only → emit `SymbolTouched`/`SignatureChanged`. |
| `SessionEnd` | Emit `IntentClosed` and release leases. |

The hooks enforce the checks. The agent does not have to remember to call the broker.

**MCP server tools:** `declare_intent`, `check_collision`, `get_contract`, `get_stub`, `propose_contract`, `resolve`.

**Live dashboard:** a web view of the symbol graph. Leased nodes light up in each developer's color. Collisions show as red edges. This view is the core of the pitch demo.

---

## 8. Novelty against prior art

| Capability | Augment / Cursor | GitKraken | Agent teams / Agent Mail | **GrokMesh** |
|---|---|---|---|---|
| Sees uncommitted work | Own only | No | No | **Whole team** |
| Granularity | Chunk | Line | File | **Symbol + contract** |
| Understands meaning | Yes | No | No | **Yes** |
| Works across developers | No | Yes | Partial | **Yes** |
| Resolves, not only detects | No | No | Messaging only | **Stubs + negotiation** |

---

## 9. Stack

| Component | Choice |
|---|---|
| Store | SQLite + `sqlite-vec` (vectors) + FTS5 (BM25) + edge table (graph) |
| Parser | tree-sitter, one language for the MVP (Python) |
| API diff | Griffe (Python) |
| Embeddings | Local code embedding model, e.g. `jina-embeddings-v2-base-code` |
| LLM | Grok: structured intent extraction and collision judge |
| Broker | FastAPI + pub/sub |
| Agent access | MCP server + agent hooks |
| Dashboard | Web graph view with live updates |

---

## 10. Hackathon build order

1. **Broker core:** SQLite schema, event log, projections. *(~3 h)*
2. **Indexer:** tree-sitter for Python, SCIP-style IDs, local embeddings. *(~3 h)*
3. **Hooks + MCP server:** prompt submit, pre-edit, post-edit. *(~3 h)*
4. **Detection stages 1–3.** *(~2 h)*
5. **Grok judge (stage 4) and structured intent extraction.** *(~2 h)*
6. **Dashboard:** graph view with live updates. *(~3 h)*
7. **Stretch:** stub generation and negotiation.

### Demo script

1. Dev A starts "JWT issuance", and `auth.hash_token()` lights up on the dashboard.
2. Dev B asks for a token-hashing util. GrokMesh blocks it and points to Dev A's symbol.
3. Dev B's agent switches to an import of the stub and continues.
4. Dev A changes the signature. Dev B's agent immediately gets a broken-contract warning.

**Credibility:** Ship a small benchmark of seeded collision scenarios. Report precision and recall for each detection stage.

---

## 11. Risks

| Risk | Mitigation |
|---|---|
| False positives annoy developers | Run the cascade. Block only on stages 1–2. Stages 3–4 only warn. |
| Leakage of uncommitted work | Run local-first. Publish only signatures and summaries. Let developers opt in per scope. |
| Hook latency | Keep the pre-edit path deterministic, with no LLM call. |
| Stale state | Use lease TTLs and heartbeats. Fold overlays into the base on merge. |
| Only one language supported | The tree-sitter grammars make extension cheap, so list it as future work. |

---

## 12. Fit for the jury

- **Callstack** is a software agency. Teams of 5–10 developers on one client repository is its everyday reality.
- **"Bot as teammate":** GrokMesh puts this theme into practice for a whole human team, not one user.

---

## References

- [Augment: real-time codebase index](https://www.augmentcode.com/blog/a-real-time-index-for-your-codebase-secure-personal-scalable)
- [Augment Context Engine MCP docs](https://docs.augmentcode.com/context-services/mcp/overview.md)
- [GitKraken Conflict Prevention](https://help.gitkraken.com/gitkraken-desktop/conflict-prevention)
- [MCP Agent Mail](https://github.com/Dicklesworthstone/mcp_agent_mail)
- [Claude Code agent teams (third-party guide)](https://www.morphllm.com/claude-code-agent-teams)
