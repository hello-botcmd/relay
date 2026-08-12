import sys
import os
import asyncio
import logging
from pyrogram import Client, idle
from pytgcalls import PyTgCalls

import config
from relay.manager import RelayManager
from commands.controls import register_controls

# Configure detailed logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def create_pyrogram_client(session_val: str, default_name: str) -> Client:
    """Helper to instantiate Pyrogram Client handling both Session Strings and Session File Names."""
    session_val = (session_val or "").strip()
    # Pyrogram String Sessions are long Base64 strings (typically > 50 characters)
    if len(session_val) > 50:
        logger.info(f"Using String Session for '{default_name}'")
        return Client(
            name=default_name,
            session_string=session_val,
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            in_memory=True
        )
    else:
        session_name = session_val or default_name
        session_path = os.path.join("sessions", session_name)
        logger.info(f"Using Session File '{session_path}'")
        return Client(
            name=session_path,
            api_id=config.API_ID,
            api_hash=config.API_HASH
        )

async def main():
    logger.info("Initializing VC Audio Relay Bot...")

    if not config.API_ID or not config.API_HASH:
        logger.error("API_ID or API_HASH missing! Please configure .env file.")
        sys.exit(1)

    os.makedirs("sessions", exist_ok=True)

    # Check if single account mode or dual account mode
    is_single_account = (config.SESSION_LISTENER == config.SESSION_BROADCASTER) or bool(os.getenv("SESSION_NAME"))

    if is_single_account:
        logger.info("🔑 Operating in SINGLE-ACCOUNT Mode (1 Pyrogram account handling both VC1 and VC2)...")
        app = create_pyrogram_client(config.SESSION_NAME, "single_account")
        listener_app = app
        broadcaster_app = app
        clients_to_start = [app]

        single_call = PyTgCalls(app)
        listener_call = single_call
        broadcaster_call = single_call
        calls_to_start = [single_call]
    else:
        logger.info("🔑 Operating in DUAL-ACCOUNT Mode (2 separate accounts)...")
        listener_app = create_pyrogram_client(config.SESSION_LISTENER, "listener_account")
        broadcaster_app = create_pyrogram_client(config.SESSION_BROADCASTER, "broadcaster_account")
        clients_to_start = [listener_app, broadcaster_app]

        listener_call = PyTgCalls(listener_app)
        broadcaster_call = PyTgCalls(broadcaster_app)
        calls_to_start = [listener_call, broadcaster_call]

    # Initialize Relay Manager Orchestrator
    relay_manager = RelayManager(
        listener_client=listener_app,
        listener_call=listener_call,
        broadcaster_client=broadcaster_app,
        broadcaster_call=broadcaster_call
    )

    # Register command controls
    register_controls(listener_app, relay_manager)

    logger.info("Starting Pyrogram client(s) and PyTgCalls engine(s)...")

    try:
        for client in clients_to_start:
            await client.start()

        for call in calls_to_start:
            await call.start()
    except Exception as start_err:
        logger.exception(f"❌ Error during client startup: {start_err}")
        return

    logger.info("✅ All clients started successfully!")
    logger.info("🤖 Bot is active. Send /startrelay or /status in Telegram.")

    try:
        await idle()
    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.info("Keyboard interrupt received.")
    finally:
        logger.info("Shutting down clients...")
        try:
            await relay_manager.stop_relay()
        except Exception as e:
            logger.warning(f"Error stopping relay: {e}")

        for client in clients_to_start:
            try:
                await client.stop()
            except Exception as e:
                logger.warning(f"Error stopping client: {e}")

        logger.info("Shutdown complete.")
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(0)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)
