
import asyncio
import os
import sys

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from engines.openclaw import get_openclaw

async def test():
    client = get_openclaw()
    print(f"Checking health at {client.host}...")
    state = await client.check_health()
    print(f"Status: {state.status}")
    print(f"Version: {state.version}")
    print(f"Error: {state.error}")

if __name__ == "__main__":
    asyncio.run(test())
