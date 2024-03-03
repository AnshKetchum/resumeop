from web_voyager.bbox import call_agent
from dotenv import load_dotenv
import asyncio


async def exec():
    res = await call_agent("Write me a detailed company brief of AMD Inc.")
    print(f"Final response: {res}")

asyncio.run(exec())
