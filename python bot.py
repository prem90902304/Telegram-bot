import json
import logging
from pathlib import Path
from datetime import datetime
import dateparser
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from nlp_handler import nlp_handler  # Import NLP file

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

TASKS_FILE = Path("tasks.json")


def load_tasks():
    if TASKS_FILE.exists():
        with open(TASKS_FILE, "r") as f:
            return json.load(f)
    else:
        return {}


def save_tasks(tasks):
    with open(TASKS_FILE, "w") as f:
        json.dump(tasks, f)


user_tasks = load_tasks()


async def addtask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    task = " ".join(context.args)
    if not task:
        await update.message.reply_text("Please specify the task after /addtask.")
        return

    user_tasks.setdefault(user_id, [])
    task_id = len(user_tasks[user_id]) + 1
    user_tasks[user_id].append({"id": task_id, "task": task, "done": False, "time": None})
    save_tasks(user_tasks)

    await update.message.reply_text(f"Task added: {task} (ID: {task_id})")


async def listtasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    tasks = user_tasks.get(user_id, [])
    if not tasks:
        await update.message.reply_text("Your task list is empty.")
        return

    message = "Your tasks:\n"
    for t in tasks:
        status = "✅" if t["done"] else "❌"
        time_info = f" at {t['time']}" if t.get("time") else ""
        message += f"{t['id']}. {t['task']} [{status}]{time_info}\n"
    await update.message.reply_text(message)


async def donetask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not context.args:
        await update.message.reply_text("Please specify the task ID to mark done: /donetask <task_id>")
        return
    try:
        task_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("Task ID must be a number.")
        return

    tasks = user_tasks.get(user_id, [])
    for t in tasks:
        if t["id"] == task_id:
            if t["done"]:
                await update.message.reply_text("Task is already marked as done.")
                return
            t["done"] = True
            save_tasks(user_tasks)
            await update.message.reply_text(f"Task marked done: {t['task']}")
            return
    await update.message.reply_text("Task ID not found.")


async def remindme(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = " ".join(context.args)
    if " at " not in text.lower():
        await update.message.reply_text("Please use format: /remindme <task> at <time>")
        return

    task_text, time_str = text.rsplit(" at ", 1)

    remind_time = dateparser.parse(time_str, settings={"PREFER_DATES_FROM": "future"})
    if not remind_time:
        await update.message.reply_text("Couldn't understand the time.")
        return

    delay = (remind_time - datetime.now()).total_seconds()
    if delay <= 0:
        await update.message.reply_text("The time is in the past! Please give a future time.")
        return

    # Store task
    user_tasks.setdefault(user_id, [])
    task_id = len(user_tasks[user_id]) + 1
    user_tasks[user_id].append({
        "id": task_id,
        "task": task_text,
        "done": False,
        "time": remind_time.strftime("%Y-%m-%d %H:%M")
    })
    save_tasks(user_tasks)

    # Schedule reminder
    context.job_queue.run_once(
        lambda ctx: ctx.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"🔔 Reminder: {task_text}"
        ),
        when=delay
    )

    await update.message.reply_text(f"Reminder set for {remind_time.strftime('%I:%M %p')} — {task_text}")


async def periodic_reminder(context):
    for user_id, tasks in user_tasks.items():
        pending_tasks = [t["task"] for t in tasks if not t["done"]]
        if pending_tasks:
            msg = "🔔 You have pending tasks:\n" + "\n".join(f"- {task}" for task in pending_tasks)
            try:
                await context.bot.send_message(chat_id=int(user_id), text=msg)
            except Exception as e:
                logging.warning(f"Failed to send reminder to {user_id}: {e}")


def main():
    BOT_TOKEN = "8422298566:AAGryCvC5j6a7osSwRW-dkcCYy0hzCv350U"

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("addtask", addtask))
    app.add_handler(CommandHandler("listtasks", listtasks))
    app.add_handler(CommandHandler("donetask", donetask))
    app.add_handler(CommandHandler("remindme", remindme))

    # NLP handler for plain text
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, nlp_handler))

    app.job_queue.run_repeating(periodic_reminder, interval=3600, first=10)

    print("Bot started...")
    app.run_polling()


if __name__ == "__main__":
    main()
