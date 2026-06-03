import asyncio
import os

async def run_background_task(coro):
    """
    Ejecuta una corrutina. 
    En tests (APP_ENV == 'test'): espera a que termine (await).
    En producción: dispara en segundo plano (create_task).
    """
    if os.getenv("APP_ENV") == "test":
        await coro
    else:
        asyncio.create_task(coro)
