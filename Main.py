import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, filters, MessageHandler
from Calculations import crossover_calculation
import asyncio
import json
import os

bot_username = os.environ["BotName"]
token = os.environ["BotToken"]

task_information = {}
running_tasks = {}

# Commands # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

async def crossover_input(update: Update, context):
    try:
        params = context.args
        if len(params) == 4:
            allowed_interval = ["1m", "2m", "5m", "15m", "30m", "60m", "90m", "1h", "1d", "5d", "1wk", "1mo", "3mo"]
            ticker = params[0]
            type_param = params[1]
            interval = params[2]
            update_interval = int(params[3])

            if "close" in type_param or "CLOSE" in type_param:
                type_param = type_param.replace("close", "Close")
                type_param = type_param.replace("CLOSE", "Close")

            if interval not in allowed_interval:
                await update.message.reply_text("Bitte geben Sie einen gültigen Chart-Intervall ein:\n"
                                                "[1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo]\n"
                                                "Für Hilfe nutzen Sie den Befehl /help.")
                return

        elif len(params) == 1:
            type_param: str = "Close"
            ticker: str = params[0]
            interval: str = "30m"
            update_interval: int = int(600)

        else:
            await update.message.reply_text("Bitte geben Sie: <ticker>, <type>, <interval>, <update> oder mindestens <ticker> ein.")
            return

        # Generates the ChatID out of the Update variable.
        chat_id = update.message.chat_id

        ticker = ticker.upper()

        # Sets an ID for the Task
        task_id = str(ticker)

        # Start calculate_signals using asyncio
        loop = asyncio.get_event_loop()
        task = loop.create_task(crossover_calculation(chat_id, type_param, ticker, interval, update_interval))
        task_information[task_id] = task

        await add_running_task(True, task_id, chat_id, type_param, ticker, interval, update_interval)

        # Respond with the task ID
        response_message = (f"Task gestartet mit dem Namen: {task_id}\n"
                            f"Ticker: {ticker}\n"
                            f"Type: {type_param}\n"
                            f"Chart Interval: {interval}\n"
                            f"Update Interval: {update_interval}s")
        await update.message.reply_text(response_message)

    except (IndexError, ValueError) as e:
        await update.message.reply_text(
            'Fehler beim Verarbeiten der Parameter. Bitte geben Sie die Parameter korrekt ein.')

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

async def add_running_task(update_json: bool, task_id: str, chat_id: str, type_param: str, ticker: str, interval: str, update_interval: int):
        creation_time = str(datetime.datetime.now())
        running_tasks[task_id] = {
            "creation_time": creation_time,
            "chat_id": chat_id,
            "type_param": type_param,
            "ticker": ticker,
            "interval": interval,
            "update_interval": update_interval
        }
        if update_json:
            with open('running_tasks.json', 'w') as file:
                json.dump(running_tasks, file)


async def update_running_task():
    with open('running_tasks.json', 'w') as file:
        json.dump(running_tasks, file)


async def stop_task(update: Update, context):
    try:
        task_id = context.args[0]
        task = task_information.get(task_id)

        if task:
            task.cancel()
            await update.message.reply_text(f"Der Task mit dem Namen {task_id} wurde gestoppt.")
            del task_information[task_id]
            del running_tasks[task_id]
            await update_running_task()

        else:
            await update.message.reply_text("Es gibt keinen laufenden Task mit dieser ID.")
    except IndexError:
        await update.message.reply_text("Bitte geben Sie eine Task-ID an.")


def run_saved_tasks():

    with open('running_tasks.json', 'r') as file:
        file_content = file.read().strip()

    if file_content:

        saved_tasks = json.loads(file_content)

        with open('running_tasks.json', 'w') as file:
            file.write('')

        for task_id, task_info in saved_tasks.items():
            chat_id = task_info["chat_id"]
            type_param = task_info["type_param"]
            ticker = task_info["ticker"]
            interval = task_info["interval"]
            update_interval = int(task_info["update_interval"])

            # asyncio.create_task muss innerhalb einer laufenden Event-Loop ausgeführt werden.
            loop = asyncio.get_event_loop()
            task = loop.create_task(crossover_calculation(chat_id, type_param, ticker, interval, update_interval))
            task_information[task_id] = task
            print(task_id)
            loop.create_task(add_running_task(True, task_id, chat_id, type_param, ticker, interval, update_interval))

    else:
        print("Es liegen keine gespeicherten Tasks vor!")


async def start_description(update: Update, context):
    start_message = (
        "**Willkommen beim Stock Prediction and Signal Bot! 📈🤖**\n\n"
        "Dieser Bot hilft Ihnen, Aktienanalysen durchzuführen und Handelssignale basierend auf gleitenden Durchschnitten (SMA) zu erhalten. Hier sind die verfügbaren Befehle:\n\n"
        "1. /help - Zeigt eine Hilfenachricht an.\n\n"
        "2. /crossover <type> <ticker> <interval> <update_interval> - \n"
        "   Startet die Aktienanalyse.\n"
        "   - type: Der zu analysierende Wert (z.B. `open`, `high`, `close`).\n"
        "   - ticker: Das Aktiensymbol (z.B. `AAPL` für Apple).\n"
        "   - interval: Das Zeitintervall für die Analyse (z.B. `1m`, `5m`, `1h`).\n"
        "   - update_interval: Die Aktualisierungsfrequenz in Sekunden \n"
        "     (z.B. `60` für 1 Minute).\n\n"
        "3. /stop <task_id> - Stoppt eine laufende Analyse.\n"
        "   - task_id: Die eindeutige ID des zu stoppenden Tasks.\n\n"
        "Beispiele:\n"
        "   - Starten einer Analyse: `/crossover AAPL close 1m 60` or \n"
        "    `/crossover AAPL`\n"
        "   - Stoppen einer Analyse: `/stop AAPL`\n\n"
        "Falls Sie Fragen haben oder Unterstützung benötigen, zögern Sie nicht, uns zu kontaktieren. Viel Erfolg beim Handeln!"
    )
    await update.message.reply_text(start_message, parse_mode='Markdown')

async def help_description(update: Update, context):
    help_message = (
        "/help\n"
        "/crossover <ticker> or <ticker>, <type>, <interval>, <update>\n"
        "/stop <taskid>\n"
    )
    await update.message.reply_text(help_message, parse_mode='Markdown')

# Responses
def handle_response(text: str) -> str:
    processed: str = text.lower()
    if "hallo" in processed:
        return "Hallo, ich bin bereit und funktioniere einwandfrei!"

    return "Leider kann ich dir bei deiner Anfrage nicht weiterhelfen. Verwende /start oder /help, um zu sehen, was ich für dich tun kann."

async def handle_message(update: Update, context):
    message_type: str = update.message.chat.type
    text: str = update.message.text

    print(f"User ({update.message.chat.id}) in {message_type}: '{text}'")

    if message_type == "group":
        if bot_username in text:
            new_text: str = text.replace(bot_username, "").strip()
            response = handle_response(new_text)
        else:
            return
    else:
        response: str = handle_response(text)

    print("Bot:", response)
    await update.message.reply_text(response)

if __name__ == "__main__":
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("crossover", crossover_input))
    app.add_handler(CommandHandler("stop", stop_task))
    app.add_handler(CommandHandler("start", start_description))
    app.add_handler(CommandHandler("help", help_description))

    run_saved_tasks()
    # Messages
    app.add_handler(MessageHandler(filters.TEXT, handle_message))
    app.run_polling(poll_interval=3)
