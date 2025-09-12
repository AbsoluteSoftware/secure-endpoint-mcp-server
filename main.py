#
#  Copyright (c) 2025. Absolute Software Corporation. All rights reserved.
#
#  This software code is licensed under and subject to the terms of
#  the MIT License as set out in the License.txt file.
#

import asyncio

from secure_endpoint_mcp.config.logging import get_logger
from secure_endpoint_mcp.server.mcp_server import mcp_server

logger = get_logger(__name__)


async def main() -> None:
    """Start the MCP server."""
    try:
        await mcp_server.start()
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Error starting MCP server: {str(e)}")
        raise
    finally:
        await mcp_server.stop()


if __name__ == "__main__":
    asyncio.run(main())
