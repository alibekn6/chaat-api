# Telegram Bot Template: Knowledge Base Q&A
# This script is auto-generated but based on a fixed, reliable template.

import os
import logging
import asyncio
import openai
import chromadb
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- Configuration ---
BOT_ID = "{{BOT_ID}}"
TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHROMA_DB_PATH = "/app/db/chroma_db"
COLLECTION_NAME = f"bot_{BOT_ID}_kb"

# --- Messages (AI Generated) ---
START_MESSAGE = """{{START_MESSAGE}}"""
NOT_FOUND_MESSAGE = """{{NOT_FOUND_MESSAGE}}"""
RAG_SYSTEM_PROMPT = """{{RAG_SYSTEM_PROMPT}}"""

# --- Setup ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize clients
openai_client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

try:
    collection = chroma_client.get_collection(name=COLLECTION_NAME)
    logger.info(f"Successfully connected to ChromaDB collection: {COLLECTION_NAME}")
except Exception as e:
    logger.error(f"Could not connect to ChromaDB collection '{COLLECTION_NAME}'. Bot may not function. Error: {e}")
    collection = None


# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message when the /start command is issued."""
    await update.message.reply_text(START_MESSAGE)


# --- Message Handlers ---
async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles user questions using the knowledge base."""
    user_question = update.message.text
    chat_id = update.message.chat_id

    logger.info(f"Question from {chat_id}: {user_question}")

    if not collection:
        await update.message.reply_text("Извините, база знаний недоступна. Попробуйте позже.")
        return

    await context.bot.send_chat_action(chat_id=chat_id, action='typing')

    try:
        # Generate embedding for the user's question
        embeddings_response = await openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=[user_question]
        )
        query_embedding = embeddings_response.data[0].embedding

        # Retrieve relevant context from ChromaDB
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=4
        )

        if not results['documents'] or not results['documents'][0]:
            await update.message.reply_text(NOT_FOUND_MESSAGE)
            return

        # Combine retrieved documents
        retrieved_context = "\n\n---\n\n".join(results['documents'][0])
        logger.info(f"Retrieved {len(results['documents'][0])} chunks for context")

        # Generate answer using OpenAI
        response = await openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": RAG_SYSTEM_PROMPT},
                {"role": "user", "content": f"Context:\n{retrieved_context}\n\nQuestion:\n{user_question}"}
            ],
            temperature=0.3
        )

        answer = response.choices[0].message.content
        await update.message.reply_text(answer)
        logger.info("Response sent successfully")

    except Exception as e:
        logger.error(f"Error processing question for chat_id {chat_id}: {e}")
        await update.message.reply_text(NOT_FOUND_MESSAGE)


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
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_question))

    logger.info("Q&A Bot is starting...")
    application.run_polling()


if __name__ == "__main__":
    main() 