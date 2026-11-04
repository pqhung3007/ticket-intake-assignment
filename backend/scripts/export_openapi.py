"""Write the OpenAPI spec to stdout (used to generate the frontend's typed API client).

uv run python -m scripts.export_openapi > ../frontend/openapi.json
"""

import json
import sys

from app.core.config import Settings
from app.main import create_app


def main() -> None:
    # Building the app does not connect to the database (that happens in the lifespan).
    settings = Settings(
        database_url="postgresql://unused/unused",
        auth_mode="password",
        session_secret="x" * 32,
    )
    json.dump(create_app(settings).openapi(), sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
