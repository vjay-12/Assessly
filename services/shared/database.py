import os
import asyncio
import logging
import socket
import urllib.parse
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/assessly")

# Keep track of any DNS patches so they stay active for the runtime
_DNS_PATCHES = {}
_original_getaddrinfo = socket.getaddrinfo


class DB:
    """Mutable container so consumers see updates after init_engine() runs."""
    engine = None
    AsyncSessionLocal = None


def _resolve_hostname(hostname: str) -> tuple[str, bool]:
    """Resolve hostname. Returns (host_to_use, used_fallback)."""
    # If already patched, assume DNS was broken and skip repeated checks
    if hostname in _DNS_PATCHES:
        return _DNS_PATCHES[hostname], True

    try:
        socket.getaddrinfo(hostname, None)
        return hostname, False
    except socket.gaierror:
        pass

    try:
        import dns.resolver
        resolver = dns.resolver.Resolver()
        resolver.nameservers = ["8.8.8.8", "8.8.4.4"]
        answers = resolver.resolve(hostname, "A")
        ip = str(answers[0])
        logger.warning(
            "System DNS failed for %s. Fallback to Google DNS -> %s", hostname, ip
        )
        # Install a persistent monkey-patch for this hostname so all future
        # connections (including pool reconnects) use the resolved IP while
        # preserving the hostname for SSL SNI verification.
        _DNS_PATCHES[hostname] = ip

        def _patched_getaddrinfo(addr, port, family=0, type=0, proto=0, flags=0):
            if addr == hostname:
                return _original_getaddrinfo(ip, port, family, type, proto, flags)
            return _original_getaddrinfo(addr, port, family, type, proto, flags)

        socket.getaddrinfo = _patched_getaddrinfo
        return ip, True
    except Exception as e:
        logger.warning("Fallback DNS also failed for %s: %s", hostname, e)
        return hostname, False


def _create_engine(url: str):
    parsed = urllib.parse.urlparse(url)
    hostname = parsed.hostname
    _resolve_hostname(hostname)

    return create_async_engine(
        url,
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        connect_args={
            "timeout": 60,
            "command_timeout": 60,
            "server_settings": {"jit": "off"},
        },
    )


async def init_engine(retries: int = 10, base_delay: float = 2.0):
    """Initialize the engine with retry logic for transient DNS failures."""
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            DB.engine = _create_engine(DATABASE_URL)
            # Test connection
            async with DB.engine.connect() as conn:
                from sqlalchemy import text
                result = await conn.execute(text("SELECT 1"))
                assert result.scalar() == 1
            DB.AsyncSessionLocal = async_sessionmaker(
                DB.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )
            logger.info("Database engine initialized successfully")
            return
        except Exception as e:
            last_error = e
            if DB.engine:
                await DB.engine.dispose()
                DB.engine = None
            delay = min(base_delay * (2 ** (attempt - 1)), 30)
            logger.warning(
                "DB connection attempt %d/%d failed: %s. Retrying in %.1fs...",
                attempt, retries, e, delay
            )
            if attempt < retries:
                await asyncio.sleep(delay)
    logger.error("Failed to connect to database after %d attempts: %s", retries, last_error)
    raise last_error


async def get_db():
    if DB.AsyncSessionLocal is None:
        raise RuntimeError("Database engine not initialized. Call init_engine() first.")
    async with DB.AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
