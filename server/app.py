"""
OpenEnv entry point — uses create_app() to build the FastAPI app with all
required endpoints (/health, /metadata, /schema, /mcp, /reset, /step, /state).
"""

from openenv.core.env_server.http_server import create_app

from server.environment import ModerationEnvironment
from server.models import ModerationAction, ModerationObservation


# Create the app using the OpenEnv framework
app = create_app(
    ModerationEnvironment,
    ModerationAction,
    ModerationObservation,
    env_name="music-content-moderation",
    max_concurrent_envs=1,
)


def main(host: str = "0.0.0.0", port: int = 7860) -> None:
    """Entry point for direct execution via uv run or python -m."""
    import uvicorn

    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
