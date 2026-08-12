import logging
import asyncio
from pyrogram import Client
from pytgcalls import PyTgCalls
from relay.buffer import JitterBuffer
from relay.listener import VC1Listener
from relay.broadcaster import VC2Broadcaster
import config

logger = logging.getLogger(__name__)

class RelayManager:
    """
    Central Manager orchestrating the Voice Chat Relay system.
    Coordinates Account 1 (Listener), JitterBuffer, and Account 2 (Broadcaster).
    """
    def __init__(self, listener_client: Client, listener_call: PyTgCalls, broadcaster_client: Client, broadcaster_call: PyTgCalls):
        self.listener_client = listener_client
        self.listener_call = listener_call
        self.broadcaster_client = broadcaster_client
        self.broadcaster_call = broadcaster_call

        self.buffer = JitterBuffer(
            target_delay_sec=config.TARGET_DELAY_SEC,
            max_delay_sec=config.MAX_DELAY_SEC,
            frame_duration_sec=config.FRAME_DURATION_SEC
        )

        self.listener = VC1Listener(self.listener_client, self.listener_call, self.buffer)
        self.broadcaster = VC2Broadcaster(self.broadcaster_client, self.broadcaster_call, self.buffer)
        self.is_relaying = False
        self.chat_vc1 = config.CHAT_VC1
        self.chat_vc2 = config.CHAT_VC2

    async def start_relay(self, chat_vc1=None, chat_vc2=None):
        """Start recording from VC1 and broadcasting to VC2."""
        if self.is_relaying:
            return False, "Relay is already running! Use /stoprelay first."

        self.chat_vc1 = chat_vc1 or self.chat_vc1 or config.CHAT_VC1
        self.chat_vc2 = chat_vc2 or self.chat_vc2 or config.CHAT_VC2

        if not self.chat_vc1 or not self.chat_vc2:
            return False, "Missing VC1 or VC2 Chat IDs! Please check config or specify in command."

        logger.info(f"Initiating relay from VC1 ({self.chat_vc1}) -> VC2 ({self.chat_vc2})")

        self.buffer.clear()
        self.is_relaying = True

        try:
            # 1. Start Listener in VC1
            await self.listener.start(self.chat_vc1)

            # 2. Start Broadcaster in VC2
            await self.broadcaster.start(self.chat_vc2)

            return True, f"✅ **Relay Started!**\n🎧 Listening: `{self.chat_vc1}`\n📢 Broadcasting: `{self.chat_vc2}`\n⏱️ Target Cushion: `{self.buffer.target_delay_sec}s`"
        except Exception as e:
            logger.error(f"Failed to start relay: {e}")
            await self.stop_relay()
            return False, f"❌ Failed to start relay: {str(e)}"

    async def stop_relay(self):
        """Stop listening and broadcasting, flush buffer."""
        if not self.is_relaying:
            return False, "Relay is not running."

        logger.info("Stopping voice chat relay...")
        self.is_relaying = False

        # Stop both sides in parallel
        await asyncio.gather(
            self.listener.stop(),
            self.broadcaster.stop(),
            return_exceptions=True
        )

        self.buffer.clear()
        return True, "🛑 **Relay Stopped cleanly.**"

    def set_target_delay(self, seconds: float):
        """Update buffer target delay cushion."""
        self.buffer.set_target_delay(seconds)
        return f"⏱️ Target delay cushion set to `{seconds}s`."

    def get_status(self) -> str:
        """Return formatted human-readable status overview."""
        stats = self.buffer.get_stats()
        status_icon = "🟢 RUNNING" if self.is_relaying else "🔴 STOPPED"

        msg = (
            f"📊 **VC Relay Status**: {status_icon}\n"
            f"──────────────────\n"
            f"🎧 **VC1 (Listener)**: `{self.chat_vc1 or 'Not Set'}`\n"
            f"📢 **VC2 (Broadcaster)**: `{self.chat_vc2 or 'Not Set'}`\n"
            f"⏱️ **Target Cushion**: `{stats['target_delay_seconds']}s`\n"
            f"📦 **Current Buffer**: `{stats['buffered_seconds']}s` ({stats['buffered_chunks']} chunks)\n"
            f"🔄 **State**: `{'Buffering cushion...' if stats['is_buffering'] and self.is_relaying else ('Relaying live' if self.is_relaying else 'Idle')}`\n"
            f"📈 **Total Frames Recv**: `{stats['total_received']}`\n"
            f"📉 **Dropped Overflows**: `{stats['total_dropped']}`\n"
            f"⏰ **Uptime**: `{stats['uptime_seconds']}s`"
        )
        return msg
