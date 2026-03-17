import os
import logging
import httpx
from fastapi import FastAPI, Request, Query, HTTPException

# --- Config ---
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")

WHATSAPP_API_URL = (
    f"https://graph.facebook.com/v21.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="WhatsApp Webhook")


# --- Health check ---
@app.get("/")
async def health():
    return {"status": "ok", "service": "whatsapp-webhook"}


# --- Webhook verification (Meta sends GET) ---
@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    if hub_mode == "subscribe" and hub_verify_token == WHATSAPP_VERIFY_TOKEN:
        logger.info("Webhook verified successfully")
        return int(hub_challenge)
    logger.warning("Webhook verification failed")
    raise HTTPException(status_code=403, detail="Verification failed")


# --- Incoming messages (Meta sends POST) ---
@app.post("/webhook")
async def receive_message(request: Request):
    body = await request.json()
    logger.info(f"Received webhook: {body}")

    # Extract message from the nested structure
    entry = body.get("entry", [])
    for e in entry:
        for change in e.get("changes", []):
            value = change.get("value", {})
            messages = value.get("messages", [])

            for message in messages:
                sender = message["from"]  # phone number e.g. "4917612345678"
                msg_type = message["type"]

                if msg_type == "text":
                    text = message["text"]["body"]
                    logger.info(f"Text from {sender}: {text}")

                    # --- Your logic here ---
                    reply = await handle_message(sender, text)
                    await send_text_message(sender, reply)

                elif msg_type == "image":
                    logger.info(f"Image from {sender}")
                    await send_text_message(sender, "Got your image! 📷")

                elif msg_type == "audio":
                    logger.info(f"Audio from {sender}")
                    await send_text_message(sender, "Got your voice message! 🎤")

                else:
                    logger.info(f"Unsupported message type: {msg_type} from {sender}")

    return {"status": "ok"}


# --- Your message handling logic ---
async def handle_message(sender: str, text: str) -> str:
    """
    Process incoming text and return a reply.
    Replace this with your own logic (LLM call, database lookup, etc.)
    """
    # Simple echo for now — replace with your business logic
    return f"You said: {text}"


# --- Send a text message via WhatsApp Cloud API ---
async def send_text_message(to: str, text: str):
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(WHATSAPP_API_URL, headers=headers, json=payload)
        if response.status_code == 200:
            logger.info(f"Message sent to {to}")
        else:
            logger.error(f"Failed to send to {to}: {response.status_code} {response.text}")

    return response