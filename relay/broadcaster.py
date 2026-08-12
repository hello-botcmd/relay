import os
import logging
import asyncio
from pyrogram import Client
from pytgcalls import PyTgCalls
from pytgcalls.types import AudioQuality, MediaStream
from relay.buffer import JitterBuffer
import config

logger = logging.getLogger(__name__)

RAW_AUDIO_PATH = os.path.join("data", "relay_audio.wav")

class VC2Broadcaster:
    """
    Broadcaster client connected to Voice Chat 2 (VC2).
    Streams live recorded audio from RAW_AUDIO_PATH into VC2.
    """
    def __init__(self, client: Client, call_py: PyTgCalls, buffer: JitterBuffer):
        self.client = client
        self.call_py = call_py
        self.buffer = buffer
        self.chat_id = None
        self.is_running = False

    async def start(self, chat_id):
        """Join VC2 and initiate audio broadcast from recorded stream."""
        self.chat_id = chat_id
        self.is_running = True
        logger.info(f"Broadcaster joining VC2 in chat {self.chat_id}...")

        # Auto-join group if not already joined
        try:
            await self.client.join_chat(self.chat_id)
            logger.info(f"Broadcaster joined chat: {self.chat_id}")
        except Exception as j_err:
            logger.debug(f"Broadcaster auto-join check: {j_err}")

        # Small delay cushion so listener starts recording first
        await asyncio.sleep(self.buffer.target_delay_sec)

        try:
            # Join voice call and play recorded audio stream file using PyTgCalls 2.x play method
            await self.call_py.play(
                self.chat_id,
                MediaStream(
                    RAW_AUDIO_PATH,
                    audio_parameters=AudioQuality.HIGH,
                    ffmpeg_parameters="-follow 1"
                )
            )
            # Explicitly unmute in VC2 so broadcast audio plays out loud
            try:
                await self.call_py.unmute(self.chat_id)
            except Exception as u_err:
                logger.warning(f"Unmute note: {u_err}")

            logger.info(f"Broadcaster successfully joined & streaming to VC2 in chat {self.chat_id}")
        except Exception as e:
            logger.exception(f"Error joining VC2: {e}")
            self.is_running = False
            raise e

    async def stop(self):
        """Leave VC2 and release broadcaster resources."""
        self.is_running = False
        if self.chat_id and self.call_py:
            try:
                await self.call_py.leave_call(self.chat_id)
                logger.info(f"Broadcaster left VC2 in chat {self.chat_id}")
            except Exception as e:
                logger.warning(f"Error leaving VC2: {e}")
        self.chat_id = None
