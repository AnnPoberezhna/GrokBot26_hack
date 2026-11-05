# GrokBot26_hack

**GrokMesh:** a live shared code graph that syncs the coding agents of a whole team before code collides.

Source idea and architecture: [docs/IDEA.md](docs/IDEA.md)

## Run the MCP broker

Requires Python 3.12+ and `uv`:

```sh
uv sync
uv run python -m grokmesh.server --db mesh.db
```

Connect an MCP client using Streamable HTTP at `http://127.0.0.1:8000/mcp`.
The SQLite file persists team state across restarts. The server closes its database
on shutdown. Host and port can be set with `--host` and `--port`.

| Tool | Inputs | Result |
| --- | --- | --- |
| `declare_intent` | `dev_id`, `goal`; optional `produces`, `consumes`, `modifies`, `scope` lists | An intent ID and 30-minute leases on produced/modified symbols, or `blocked: true` with competing leases. |
| `sync_file` | `dev_id`, `path`, `module`, `source`; optional `intent_id`, `ttl_s` | Published symbol IDs and renewed leases, or a blocked result. |
| `check_collision` | `dev_id`, `symbol_ids` | Competing leases or active intents and a `blocked` flag. |
| `get_contracts` | `symbol_ids` | Signatures across base and overlays, including owners and active lease state. |

`module` is the qualified Python module name, such as `pkg.auth`. `path` labels a
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
Only `produces` and `modifies` claim symbols; `consumes` and path globs are stored
as intent context. Leases expire unless renewed; active intents continue to reserve their targets until closed. Signature compatibility and
cross-file call resolution are separate upcoming features.

### Public tunnel for a shared demo

With `cloudflared` installed, start `cloudflared tunnel --url http://127.0.0.1:8000`.
Copy the assigned hostname, then start the broker with that hostname allowed:

```sh
uv run python -m grokmesh.server --db mesh.db --public-host YOUR-HOST.trycloudflare.com
```

Connect Grok Bot to `https://YOUR-HOST.trycloudflare.com/mcp`. The broker currently
assumes trusted demo participants: developer IDs are caller-supplied and there is
no authentication. Host validation remains enabled for the tunnel hostname.

Run checks with `uv run pytest`, `uv run ruff check src tests`, and `uv run mypy`.
