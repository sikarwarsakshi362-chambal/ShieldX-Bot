# ---- (everything above your file remains unchanged) ----

import requests
from datetime import datetime

# ===========================
# NSFW DETECTION (auto delete + mute)
# ===========================
NSFW_API = "https://api-inference.huggingface.co/models/Falconsai/nsfw_image_detection"
HUGGINGFACE_KEY = os.getenv("HUGGINGFACE_KEY", "")  # optional free key if you have one
headers = {"Authorization": f"Bearer {HUGGINGFACE_KEY}"} if HUGGINGFACE_KEY else {}

# Track user spam for NSFW
NSFW_TRACKER: Dict[int, List[float]] = {}

async def detect_nsfw_and_act(client, message):
    if not message.photo and not message.document:
        return
    try:
        file_path = await message.download()
        with open(file_path, "rb") as f:
            resp = requests.post(NSFW_API, headers=headers, files={"file": f})
        os.remove(file_path)

        if resp.status_code != 200:
            return

        result = resp.json()
        if isinstance(result, list) and len(result) > 0:
            label = result[0].get("label", "").lower()
            score = result[0].get("score", 0)

            if "nsfw" in label or score > 0.8:
                await client.delete_messages(message.chat.id, message.id)
                await message.reply_text(
                    f"🚫 NSFW content detected from [{message.from_user.first_name}](tg://user?id={message.from_user.id}) and deleted.",
                    disable_web_page_preview=True,
                )

                # Record user event
                uid = message.from_user.id
                now = time.time()
                if uid not in NSFW_TRACKER:
                    NSFW_TRACKER[uid] = []
                NSFW_TRACKER[uid] = [t for t in NSFW_TRACKER[uid] if now - t < 3]
                NSFW_TRACKER[uid].append(now)

                if len(NSFW_TRACKER[uid]) >= 5:
                    try:
                        await client.restrict_chat_member(
                            message.chat.id,
                            uid,
                            types.ChatPermissions(),
                        )
                        await message.reply_text(f"🔇 User muted forever due to repeated NSFW spam.")
                    except Exception:
                        pass

    except Exception as e:
        print("NSFW detection error:", e)


# ===========================
# EXTEND AUTO DELETE MONITOR
# ===========================
@app.on_message(filters.group & (filters.photo | filters.document))
async def auto_delete_monitor(client, message):
    cfg = ensure_chat(message.chat.id)
    # NSFW check (independent of auto-clean)
    asyncio.create_task(detect_nsfw_and_act(client, message))

    if not cfg.get("clean_on"):
        return
    if message.media:
        mins = cfg.get("delete_minutes", 60)
        delay = int(mins) * 60
        if delay == 0:
            try:
                await client.delete_messages(message.chat.id, message.message_id)
            except:
                pass
        else:
            asyncio.create_task(schedule_delete(client, message.chat.id, message.message_id, delay))
