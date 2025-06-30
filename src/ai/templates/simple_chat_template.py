# Telegram Bot Template: Simple Chat
# This script is auto-generated but based on a fixed, reliable template.

import os
import logging
import openai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- Configuration ---
BOT_ID = "{{BOT_ID}}"
TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# --- Static Messages (AI Generated) ---
START_MESSAGE = """{{START_MESSAGE}}"""
CHAT_SYSTEM_PROMPT = """{{CHAT_SYSTEM_PROMPT}}"""

# --- Setup ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai_client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)


# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message when the /start command is issued."""
    await update.message.reply_text(START_MESSAGE)


# --- Message Handlers ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles user messages with OpenAI chat completion."""
    user_message = update.message.text
    chat_id = update.message.chat_id

    await context.bot.send_chat_action(chat_id=chat_id, action='typing')

    try:
        # Call OpenAI API for chat completion
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": CHAT_SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
        )
        answer = response.choices[0].message.content

    except Exception as e:
        logger.error(f"Error handling message for chat_id {chat_id}: {e}")
        answer = "I encountered an error while processing your message. Please try again."

    await update.message.reply_text(answer)


def main():
    """Start the bot."""
    if not TELEGRAM_TOKEN:
        logger.error("BOT_TOKEN environment variable not set!")
        return

    if not OPENAI_API_KEY:
        logger.error("OPENAI_API_KEY environment variable not set!")
        return

    application = Application.builder().token(TELEGRAM_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Simple Chat Bot is starting...")
    application.run_polling()


if __name__ == "__main__":
    main() 