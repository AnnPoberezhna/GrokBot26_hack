# GrokBot26_hack

**GrokMesh:** a live shared code graph that syncs the coding agents of a whole team before code collides.

Source idea and architecture: [docs/IDEA.md](docs/IDEA.md)

Pitch film (55 s, no sound): [docs/grokmesh-pitch.mp4](docs/grokmesh-pitch.mp4).
Kanzen version (75 s, explains the mechanism): [docs/grokmesh-pitch-kanzen.mp4](docs/grokmesh-pitch-kanzen.mp4). Source: [pitch/](pitch/) (Remotion, `cd pitch && pnpm render`).

## Run the MCP broker

Requires Python 3.12+ and `uv`:

```sh
uv sync
uv run python -m grokmesh.server --db mesh.db --base-root path/to/main/checkout
```

`--base-root` rebuilds the base layer from a checkout of the main branch at startup.
Always set it for a demo: without a base layer, every symbol in a synced file counts
as changed, so two developers who edit different functions of one file collide.

Connect an MCP client using Streamable HTTP at `http://127.0.0.1:8000/mcp`.
The SQLite file persists team state across restarts. The server closes its database
on shutdown. Host and port can be set with `--host` and `--port`.

| Tool | Inputs | Result |
| --- | --- | --- |
| `declare_intent` | `dev_id`, `goal`; optional `produces`, `consumes`, `modifies`, `scope` lists | An intent ID and 30-minute leases on produced/modified symbols, or `blocked: true` with competing leases. |
| `sync_file` | `dev_id`, `path`, `source`; optional `module`, `intent_id`, `ttl_s` | Published symbol IDs and renewed leases, or a blocked result. |
| `check_collision` | `dev_id`, `symbol_ids` | Competing leases or active intents and a `blocked` flag. |
| `get_contracts` | `symbol_ids` | Signatures across base and overlays, including owners and active lease state. |
| `close_intent` | `dev_id`, `intent_id`; optional `status` (`done` or `abandoned`) | Close your intent and release its leases. |
| `get_activity` | Optional `dev_id` | Active goals, scopes and leased symbols grouped by developer. |
| `get_collision_digest` | Optional `dev_id` | Current collisions grouped by affected developer. |

`module` is the qualified Python module name, such as `pkg.auth`. It defaults to the
name derived from `path` (`src/pkg/auth.py` -> `pkg.auth`). `path` labels a
repository file; source must be uploaded explicitly. The server never opens that
path. Invalid Python and invalid inputs return MCP tool errors without changing
the file overlay. Collision checks and writes execute in the same database
transaction, so competing declarations cannot both claim the same symbol.

### Two-agent demo

1. Anna declares an intent with `produces: ["auth.issue"]`.
2. Marcel declares an intent with `modifies: ["auth.issue"]`. The result is blocked
   and identifies Anna's lease; Marcel's intent is not stored.
3. Anna uploads `auth.py`, module `auth`, with source defining `issue`, and passes
   her returned `intent_id` to `sync_file`.
4. Either agent requests `get_contracts` for `auth.issue` to see Anna's signature.

Bot instructions: declare intent before editing, stop when `blocked` is true,
check collisions before further edits, and sync changed source after each edit.
Call `close_intent` when finished or abandoning work, so teammates can claim the symbols.
Only `produces` and `modifies` claim symbols; `consumes` and path globs are stored
as intent context. Leases expire unless renewed; active intents continue to reserve
their targets until closed. Imported calls are resolved on a best-effort basis;
dynamic dispatch and name shadowing remain limitations.

### Public tunnel for a shared demo

With `cloudflared` installed, start `cloudflared tunnel --url http://127.0.0.1:8000`.
Copy the assigned hostname, then start the broker with that hostname allowed:

```sh
uv run python -m grokmesh.server --db mesh.db --base-root path/to/main/checkout \
  --public-host YOUR-HOST.trycloudflare.com
```

Connect Grok Bot to `https://YOUR-HOST.trycloudflare.com/mcp`. The broker currently
assumes trusted demo participants: developer IDs are caller-supplied and there is
no authentication. Host validation remains enabled for the tunnel hostname.

Run checks with `uv run pytest`, `uv run ruff check src tests`, and `uv run mypy`.


### Broken contracts

File sync classifies signature changes against the base: added, unchanged,
compatible, or breaking. Optional parameters can be added safely; removed or
renamed parameters, new required parameters, lost variadic arguments, and
sync/async changes are breaking. Annotation and class-header changes are
conservatively breaking; type subtyping and runtime behavior are not analyzed.
Changing an existing default value remains compatible by call shape.

A breaking symbol with a call edge from another developer's leased WIP symbol
produces a report naming the caller, owner, and before/after signatures.
`check_collision` and intent declaration block affected caller edits. After an
upload, `sync_file` publishes the source and returns impact warnings, allowing
the latest graph to remain visible and callers to upload their fixes. Expired
leases, unchanged base callers, and calls within one developer's work do not
produce these conflicts. Call-shape compatibility is conservative: inspect the
reported contract before deciding whether to update or escalate.

### Possible duplication (BM25 fallback)

`declare_intent` searches other developers' active intents and leased WIP symbols
for related work, even when the target symbol names differ. Results appear in
`collisions` with `kind: duplication`, `severity: warn`, and reuse/stub/escalation
suggestions. They do not block the declaration.

This is the plan's text-search fallback, using SQLite FTS5/BM25. It requires at
least two distinct shared words after filtering common English and code words,
searches up to 100 ranked candidates, and returns at most five warnings. The index
updates atomically with symbol and intent writes and backfills existing databases
on startup. Own work, closed intents, base symbols, and expired symbol leases are
excluded; active intents remain eligible until closed.

Treat matches as unconfirmed suggestions. This version cannot detect synonyms
without shared words, and words in common can still produce false positives.
Embeddings, cosine retrieval, and Grok confirmation remain upcoming features.


### Finishing work and shared Mesh Bot queries

Call `close_intent` with your `dev_id` and returned `intent_id` when work is done.
The default status is `done`; use `abandoned` when stopping without completing it.
Only the owner can close an intent. Repeated calls are safe, and leases linked to
other intents are preserved. Closing releases claims; it does not merge code into
the base or delete uploaded overlays.

A shared bot can use `get_activity` to answer "who works on what?" from active
intent goals, scopes, symbol paths and lease expiry times. An active intent remains
visible even when its leases expire, until its owner closes it.

`get_collision_digest` recomputes exact conflicts, broken contracts and unconfirmed
BM25 duplication suggestions from current state. Results are grouped by affected
developer, with blocking reports first. `report_count` counts developer reports,
so a two-person conflict may appear twice. Both tools accept an optional `dev_id`
filter and return empty lists when there is no matching activity or conflict.
These are read-only, on-demand tools; scheduled delivery and the live shared bot
connection are still to be configured.

### Presentation dashboard

Open the broker's root URL, `http://127.0.0.1:8000/`, for the dashboard. The MCP
endpoint remains at `/mcp`. Start the broker as usual; the frontend has no separate
build step or JavaScript dependencies:

```sh
uv run python -m grokmesh.server --db mesh.db --base-root path/to/main/checkout
```

The dashboard opens in **Demo** mode with three sample developers and scenarios
for exact conflicts, broken contracts and possible duplication. Sample state is
generated by the collision engine in a separate in-memory database and never
modifies team data. Select **Live workspace** to read the broker's real state,
refreshed every three seconds. The selected mode is remembered in your browser.

For your presentation, click **Present** to hide the sidebar and expand the graph.
Click any symbol or **Explore conflict** to inspect signatures, before/after
contracts and suggested next steps. Symbol search, zoom controls, contract tables,
team activity and blocking/warning filters are available; press `/` to focus search
or Escape to leave presentation mode. Mobile layouts include bottom navigation
and a horizontally scrollable graph.

The read-only `/api/dashboard` route serves live metadata; `?demo=1` serves the
isolated sample workspace. At most 18 symbols appear in the graph, prioritizing
active and affected symbols; the metric reports the total indexed context. No
source code is returned. Dashboard metadata has the same trusted-demo access
assumptions as the MCP broker.
