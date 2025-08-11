import datetime
import asyncio
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from pymongo import MongoClient
from nlp import parse_nlp_time  # Optional NLP

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")

# MongoDB setup
client = MongoClient(MONGO_URI)
db = client["reminder_bot"]
tasks_collection = db["tasks"]

# ===== Commands =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hello! 😊\nUse /remind HH:MM task\nOr just say: 'Remind me at 5 pm to drink water'"
    )

async def add_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        time_str = context.args[0]
        task = " ".join(context.args[1:])

        reminder_time = datetime.datetime.strptime(time_str, "%H:%M").replace(
            year=datetime.datetime.now().year,
            month=datetime.datetime.now().month,
            day=datetime.datetime.now().day
        )

        if reminder_time < datetime.datetime.now():
            reminder_time += datetime.timedelta(days=1)

        tasks_collection.insert_one({
            "chat_id": update.effective_chat.id,
            "task": task,
            "time": reminder_time
        })

        await update.message.reply_text(f"✅ Reminder set for {time_str} — {task}")

    except Exception:
        await update.message.reply_text("⚠ Usage: /remind HH:MM task")

async def nlp_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    reminder_time, task = parse_nlp_time(text)

    if reminder_time and task:
        tasks_collection.insert_one({
            "chat_id": update.effective_chat.id,
            "task": task,
            "time": reminder_time
        })
        await update.message.reply_text(f"✅ Reminder set for {reminder_time.strftime('%H:%M')} — {task}")
    else:
        await update.message.reply_text("❌ Sorry, I couldn't understand the time.")

# ===== Reminder Checker =====
async def check_reminders(app):
    while True:
        now = datetime.datetime.now()
        tasks = list(tasks_collection.find({"time": {"$lte": now}}))

        for task in tasks:
            try:
                await app.bot.send_message(
                    chat_id=task["chat_id"],
                    text=f"⏰ Reminder: {task['task']}"
                )
                tasks_collection.delete_one({"_id": task["_id"]})
            except Exception as e:
                print("Error sending reminder:", e)

        await asyncio.sleep(60)

# ===== Main Function =====
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("remind", add_reminder))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, nlp_reminder))

    asyncio.create_task(check_reminders(app))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
