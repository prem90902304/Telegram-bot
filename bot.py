import os
import re
import datetime
import asyncio
import dateparser
from pymongo import MongoClient
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client["mybotdb"]
reminders_collection = db["reminders"]

def parse_nlp_time(text: str):
    pattern = r"remind me (.+?) to (.+)"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None, None

    time_str = match.group(1).strip()
    task = match.group(2).strip()
    reminder_time = dateparser.parse(time_str, settings={"PREFER_DATES_FROM": "future"})
    if not reminder_time:
        return None, None

    now = datetime.datetime.now()
    if reminder_time < now:
        reminder_time += datetime.timedelta(days=1)

    return reminder_time, task

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! Send me a message like:\n"
        "'Remind me tomorrow at 5 pm to call mom'"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    reminder_time, task = parse_nlp_time(text)
    if reminder_time and task:
        reminders_collection.insert_one({
            "chat_id": update.effective_chat.id,
            "task": task,
            "reminder_time": reminder_time,
            "created_at": datetime.datetime.utcnow()
        })
        await update.message.reply_text(
            f"✅ Reminder set for {reminder_time.strftime('%Y-%m-%d %H:%M')}: {task}"
        )
    else:
        await update.message.reply_text(
            "Sorry, I couldn't understand that. Please use the format:\n"
            "'Remind me [time] to [task]'"
        )

async def reminder_worker(app):
    while True:
        now = datetime.datetime.now()
        due_reminders = list(reminders_collection.find({"reminder_time": {"$lte": now}}))
        for reminder in due_reminders:
            try:
                await app.bot.send_message(
                    chat_id=reminder["chat_id"],
                    text=f"⏰ Reminder: {reminder['task']}"
                )
                reminders_collection.delete_one({"_id": reminder["_id"]})
            except Exception as e:
                print(f"Error sending reminder: {e}")
        await asyncio.sleep(10)

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Run the reminder worker every 10 seconds
    app.job_queue.run_repeating(lambda ctx: asyncio.create_task(reminder_worker(app)), interval=10, first=10)

    print("Bot started...")
    app.run_polling()
