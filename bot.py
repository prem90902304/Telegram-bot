import os
import asyncio
from datetime import datetime
from pymongo import MongoClient
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ---- MongoDB connection ----
client = MongoClient(
    os.getenv("MONGO_URI"),
    tls=True,
    tlsAllowInvalidCertificates=True
)

db = client["reminder_bot"]
tasks_collection = db["tasks"]

# ---- Telegram Bot Token ----
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ---- Start Command ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Send /remind <time> <message> to set a reminder.")

# ---- Reminder Command ----
async def remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) < 2:
            await update.message.reply_text("Usage: /remind <HH:MM> <message>")
            return

        time_str = context.args[0]
        message = " ".join(context.args[1:])

        reminder_time = datetime.strptime(time_str, "%H:%M").replace(
            year=datetime.now().year,
            month=datetime.now().month,
            day=datetime.now().day
        )

        tasks_collection.insert_one({
            "chat_id": update.effective_chat.id,
            "time": reminder_time,
            "message": message
        })

        await update.message.reply_text(f"✅ Reminder set for {time_str} — {message}")

    except ValueError:
        await update.message.reply_text("Time must be in HH:MM format.")

# ---- Background task to check reminders ----
async def check_reminders(app):
    while True:
        now = datetime.now()
        tasks = list(tasks_collection.find({"time": {"$lte": now}}))

        for task in tasks:
            try:
                await app.bot.send_message(chat_id=task["chat_id"], text=f"⏰ Reminder: {task['message']}")
                tasks_collection.delete_one({"_id": task["_id"]})
            except Exception as e:
                print(f"Error sending reminder: {e}")

        await asyncio.sleep(60)

# ---- Main ----
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("remind", remind))

    asyncio.create_task(check_reminders(app))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())

