"""Async API wrapper for AmpliFi routers."""
import aiohttp
import asyncio
import logging

_LOGGER = logging.getLogger(__name__)

class AmpliFiAPI:
    """Async wrapper for AmpliFi router."""

    def __init__(self, host: str, username: str, password: str):
        self.host = host
        self.username = username
        self.password = password
        self._session: aiohttp.ClientSession | None = None
        self._initialized = False

    async def async_initialize(self):
        """Initialize session."""
        self._session = aiohttp.ClientSession()
        # 👇 autentificare dacă e necesar
        # În mod minimalist, facem doar test de conectivitate:
        try:
            async with self._session.get(f"http://{self.host}") as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Status {resp.status}")
        except Exception as exc:
            await self._session.close()
            _LOGGER.error("Amplifi init failed: %s", exc)
            raise

        self._initialized = True
        _LOGGER.debug("Amplifi session initialized")

    async def async_get_clients(self) -> list[dict]:
        """Return connected clients (device_tracker)."""
        if not self._initialized:
            return []

        # Exemplu simplu (de adaptat cu API real)
        await asyncio.sleep(0.1)
        return [
            {"name": "TestPhone", "mac": "AA:BB:CC:DD:EE:01", "connected": True},
        ]

    async def async_get_stats(self) -> dict:
        """Generic method for sensors."""
        if not self._initialized:
            return {}
        await asyncio.sleep(0.1)
        return {"uptime": 12345}

    async def async_close(self):
        """Close session."""
        if self._session:
            await self._session.close()
            self._initialized = False
            _LOGGER.debug("Amplifi API closed")
