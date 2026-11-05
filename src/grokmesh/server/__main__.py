"""Run with: python -m grokmesh.server --db mesh.db --base-root path/to/main/checkout"""

import argparse
import sys

from grokmesh.leases import index_base
from grokmesh.server import create_server
from grokmesh.store import Store


def main() -> None:
    parser = argparse.ArgumentParser(description="GrokMesh HTTP MCP broker")
    parser.add_argument("--db", default="mesh.db")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--public-host", help="Allowed tunnel hostname, without scheme or path")
    parser.add_argument(
        "--base-root",
        help="Checkout of the main branch. Its Python files rebuild the base layer at startup. "
        "Without a base layer, every symbol in a synced file counts as changed.",
    )
    args = parser.parse_args()
    with Store(args.db) as store:
        if args.base_root:
            report = index_base(store, args.base_root)
            print(
                f"base layer: {len(report.indexed)} files indexed, {len(report.skipped)} skipped",
                file=sys.stderr,
            )
            for path, reason in report.skipped.items():
                print(f"  skipped {path}: {reason}", file=sys.stderr)
        create_server(store, host=args.host, port=args.port, public_host=args.public_host).run(
            transport="streamable-http"
        )


if __name__ == "__main__":
    main()
