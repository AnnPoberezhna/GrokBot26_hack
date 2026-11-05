"""Run with: python -m grokmesh.server --db mesh.db"""

import argparse

from grokmesh.server import create_server
from grokmesh.store import Store


def main() -> None:
    parser = argparse.ArgumentParser(description="GrokMesh HTTP MCP broker")
    parser.add_argument("--db", default="mesh.db")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--public-host", help="Allowed tunnel hostname, without scheme or path")
    args = parser.parse_args()
    with Store(args.db) as store:
        create_server(store, host=args.host, port=args.port, public_host=args.public_host).run(
            transport="streamable-http"
        )


if __name__ == "__main__":
    main()
