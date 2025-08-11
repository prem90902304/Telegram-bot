import re
import json
from pathlib import Path
from transformers import pipeline
from telegram import Update
from telegram.ext import ContextTypes

# File to store tasks
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

# In-memory cache of tasks
user_tasks = load_tasks()

# NLP Model (Zero-shot classification)
classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")

async def nlp_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()

    intents = ["add task", "list tasks", "mark task done", "greeting"]
    result = classifier(text, intents)
    top_intent = result["labels"][0]

    if top_intent == "add task":
        task_match = re.sub(r"remind me to|add task|remember to", "", text, flags=re.IGNORECASE).strip()
        if task_match:
            user_tasks.setdefault(user_id, [])
            task_id = len(user_tasks[user_id]) + 1
            user_tasks[user_id].append({"id": task_id, "task": task_match, "done": False})
            save_tasks(user_tasks)
            await update.message.reply_text(f"Task added: {task_match} (ID: {task_id})")
        else:
            await update.message.reply_text("I couldn't find the task in your sentence.")

    elif top_intent == "list tasks":
        tasks = user_tasks.get(user_id, [])
        if not tasks:
            await update.message.reply_text("Your task list is empty.")
            return
        message = "Your tasks:\n"
        for t in tasks:
            status = "✅" if t["done"] else "❌"
            message += f"{t['id']}. {t['task']} [{status}]\n"
        await update.message.reply_text(message)

    elif top_intent == "mark task done":
        numbers = re.findall(r"\d+", text)
        if numbers:
            task_id = int(numbers[0])
            tasks = user_tasks.get(user_id, [])
            for t in tasks:
                if t["id"] == task_id:
                    t["done"] = True
                    save_tasks(user_tasks)
                    await update.message.reply_text(f"Marked done: {t['task']}")
                    return
            await update.message.reply_text("Task ID not found.")
        else:
            await update.message.reply_text("Please tell me the task number to mark done.")

    elif top_intent == "greeting":
        await update.message.reply_text("Hi there! You can tell me tasks in plain English.")

    else:
        await update.message.reply_text("Sorry, I’m not sure what you mean.")
