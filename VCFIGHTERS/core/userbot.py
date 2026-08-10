# ╔══════════════════════════════════════════════════════════════╗
# ║         VCFIGHTER — Userbot Manager                          ║
# ║         File: VCFIGHTERS/core/userbot.py                     ║
# ╚══════════════════════════════════════════════════════════════╝

from pyrogram import Client
import hashlib

import Config
from VCFIGHTERS.logging import LOGGER
from VCFIGHTERS.database.mangodb import set_userbot_active

log = LOGGER("Userbot")


def _stable_session_name(session: str) -> str:
    """Deterministic name derived from the session string. Python's built-in
    hash() is randomized per-process (security feature), so using it here
    would give each userbot a different Client `name` on every restart —
    and since Pyrogram persists a `<name>.session` file to disk by default,
    that meant a new orphaned file accumulating on every restart."""
    digest = hashlib.sha256(session.encode()).hexdigest()[:12]
    return f"ub_{digest}"


class UserbotManager:
    """
    Manages all active Pyrogram userbot clients.
    Stores them in a dict: { session_string: Client }
    """

    def __init__(self):
        # session_string → Pyrogram Client
        self._clients: dict[str, Client] = {}

    # ──────────────────────────────────────────
    # START
    # ──────────────────────────────────────────

    async def start_userbot(self, session: str) -> Client | None:
        """Start a single userbot from session string. Returns client or None on fail."""
        if session in self._clients:
            log.info(f"⚠️ Userbot already running for this session.")
            return self._clients[session]

        try:
            client = Client(
                name=_stable_session_name(session),
                api_id=Config.API_ID,
                api_hash=Config.API_HASH,
                session_string=session,
                no_updates=False,   # updates chahiye — PyTgCalls ke liye
                in_memory=True,     # session string se hi login hota hai — disk file ki zaroorat nahi
            )
            await client.start()
            me = await client.get_me()
            self._clients[session] = client
            await set_userbot_active(session, True)
            log.info(f"✅ Userbot started: {me.first_name} | +{me.phone_number}")
            return client

        except Exception as e:
            log.error(f"❌ Failed to start userbot: {e}")
            await set_userbot_active(session, False)
            return None

    async def start_all(self, sessions: list[str]):
        """Start all userbots from a list of session strings (called at boot)."""
        success = 0
        for session in sessions:
            result = await self.start_userbot(session)
            if result:
                success += 1
        log.info(f"✅ {success}/{len(sessions)} userbots started successfully")

    # ──────────────────────────────────────────
    # STOP
    # ──────────────────────────────────────────

    async def stop_userbot(self, session: str):
        """Stop a single userbot client."""
        client = self._clients.pop(session, None)
        if not client:
            log.warning("⚠️ No active client found for this session.")
            return
        try:
            await client.stop()
            await set_userbot_active(session, False)
            log.info(f"🛑 Userbot stopped.")
        except Exception as e:
            log.error(f"❌ Error stopping userbot: {e}")

    async def stop_all(self):
        """Stop all running userbot clients (called at shutdown)."""
        sessions = list(self._clients.keys())
        for session in sessions:
            await self.stop_userbot(session)
        log.info("🛑 All userbots stopped.")

    # ──────────────────────────────────────────
    # GET / CHECK
    # ──────────────────────────────────────────

    def get_client(self, session: str) -> Client:
        """
        Returns active Pyrogram Client for a session string.
        Raises KeyError if not found.
        """
        client = self._clients.get(session)
        if not client:
            raise KeyError(f"No active client for session: {session[:20]}...")
        return client

    def get_all_clients(self) -> list[Client]:
        """Returns list of all active Pyrogram Client objects."""
        return list(self._clients.values())

    def get_all_sessions(self) -> list[str]:
        """Returns list of all active session strings."""
        return list(self._clients.keys())

    def is_running(self, session: str) -> bool:
        """Check if a userbot is currently active."""
        return session in self._clients

    def count(self) -> int:
        """Total active userbots right now."""
        return len(self._clients)

    # ──────────────────────────────────────────
    # RESTART
    # ──────────────────────────────────────────

    async def restart_userbot(self, session: str) -> Client | None:
        """Stop + Start a single userbot."""
        log.info("🔄 Restarting userbot...")
        await self.stop_userbot(session)
        return await self.start_userbot(session)

    async def restart_all(self):
        """Restart all userbots."""
        sessions = list(self._clients.keys())
        log.info(f"🔄 Restarting {len(sessions)} userbot(s)...")
        for session in sessions:
            await self.restart_userbot(session)


# ─────────────────────────────────────────────
# SINGLETON — baaki sab files isko import karte hain
# ─────────────────────────────────────────────

userbot_manager = UserbotManager()

