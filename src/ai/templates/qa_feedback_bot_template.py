# Telegram Bot Template: Q&A + Feedback System
# This script is auto-generated but based on a fixed, reliable template.

import os
import logging
import asyncio
import openai
import chromadb
import httpx
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- Configuration ---
BOT_ID = "{{BOT_ID}}"
TELEGRAM_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHROMA_DB_PATH = "/app/db/chroma_db"
COLLECTION_NAME = f"bot_{BOT_ID}_kb"
FEEDBACK_API_URL = os.getenv("FEEDBACK_API_URL", "http://localhost:8000")

# --- Messages (AI Generated) ---
START_MESSAGE = """{{START_MESSAGE}}"""
NOT_FOUND_MESSAGE = """{{NOT_FOUND_MESSAGE}}"""
RAG_SYSTEM_PROMPT = """{{RAG_SYSTEM_PROMPT}}"""
FEEDBACK_WELCOME_MESSAGE = """{{FEEDBACK_WELCOME_MESSAGE}}"""
FEEDBACK_THANKS_MESSAGE = """{{FEEDBACK_THANKS_MESSAGE}}"""

# --- Feedback States ---
FEEDBACK_STATES = {
    "WAITING_RATING": "waiting_rating",
    "WAITING_TEXT": "waiting_text", 
    "WAITING_PHOTO": "waiting_photo"
}

# --- Setup ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize clients
openai_client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
http_client = httpx.AsyncClient()

def get_collection():
    """Get or reconnect to ChromaDB collection."""
    try:
        return chroma_client.get_collection(name=COLLECTION_NAME)
    except Exception as e:
        logger.error(f"Could not connect to ChromaDB collection '{COLLECTION_NAME}': {e}")
        return None

collection = get_collection()
if collection:
    logger.info(f"Successfully connected to ChromaDB collection: {COLLECTION_NAME}")
else:
    logger.error(f"Could not connect to ChromaDB collection '{COLLECTION_NAME}'. Bot may not function.")


# --- Helper Functions ---
def get_main_menu_keyboard():
    """Create main menu with Q&A and Feedback options."""
    keyboard = [
        [InlineKeyboardButton("🤖 Задать вопрос", callback_data="mode_qa")],
        [InlineKeyboardButton("💬 Оставить отзыв", callback_data="mode_feedback")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_rating_keyboard():
    """Create rating selection keyboard."""
    keyboard = [
        [InlineKeyboardButton("⭐", callback_data="rating_1"),
         InlineKeyboardButton("⭐⭐", callback_data="rating_2"),
         InlineKeyboardButton("⭐⭐⭐", callback_data="rating_3")],
        [InlineKeyboardButton("⭐⭐⭐⭐", callback_data="rating_4"),
         InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data="rating_5")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_feedback_skip_keyboard():
    """Create keyboard for skipping feedback steps."""
    keyboard = [
        [InlineKeyboardButton("⏭️ Пропустить", callback_data="skip_step")],
        [InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)


# --- Command Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends a welcome message with menu when the /start command is issued."""
    await update.message.reply_text(
        START_MESSAGE,
        reply_markup=get_main_menu_keyboard()
    )


# --- Callback Query Handlers ---
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callback queries."""
    query = update.callback_query
    await query.answer()

    if query.data == "mode_qa":
        await query.edit_message_text(
            "🤖 *Режим вопросов и ответов*\n\nЗадайте мне любой вопрос, и я найду ответ в базе знаний!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_menu")
            ]])
        )
        context.user_data["mode"] = "qa"

    elif query.data == "mode_feedback":
        await start_feedback_process(query, context)

    elif query.data.startswith("rating_"):
        rating = int(query.data.split("_")[1])
        context.user_data["feedback_rating"] = rating
        await query.edit_message_text(
            f"Спасибо за оценку: {'⭐' * rating}\n\n"
            "Теперь напишите ваш отзыв (или нажмите 'Пропустить'):",
            reply_markup=get_feedback_skip_keyboard()
        )
        context.user_data["feedback_state"] = FEEDBACK_STATES["WAITING_TEXT"]

    elif query.data == "skip_step":
        await handle_feedback_skip(query, context)

    elif query.data == "back_to_menu":
        context.user_data.clear()
        await query.edit_message_text(
            START_MESSAGE,
            reply_markup=get_main_menu_keyboard()
        )


async def start_feedback_process(query, context):
    """Start the feedback collection process."""
    await query.edit_message_text(
        FEEDBACK_WELCOME_MESSAGE + "\n\nПожалуйста, оцените наш сервис:",
        reply_markup=get_rating_keyboard()
    )
    context.user_data["mode"] = "feedback"
    context.user_data["feedback_state"] = FEEDBACK_STATES["WAITING_RATING"]


async def handle_feedback_skip(query, context):
    """Handle skipping feedback steps."""
    current_state = context.user_data.get("feedback_state")
    
    if current_state == FEEDBACK_STATES["WAITING_TEXT"]:
        # Skip text, go to photo
        await query.edit_message_text(
            "Хотите приложить фотографию к отзыву?\n(или нажмите 'Пропустить' для завершения)",
            reply_markup=get_feedback_skip_keyboard()
        )
        context.user_data["feedback_state"] = FEEDBACK_STATES["WAITING_PHOTO"]
    
    elif current_state == FEEDBACK_STATES["WAITING_PHOTO"]:
        # Skip photo, submit feedback
        await submit_feedback(query, context)


# --- Message Handlers ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages based on current mode."""
    mode = context.user_data.get("mode", "qa")
    feedback_state = context.user_data.get("feedback_state")

    if mode == "feedback" and feedback_state == FEEDBACK_STATES["WAITING_TEXT"]:
        # Collect feedback text
        context.user_data["feedback_text"] = update.message.text
        await update.message.reply_text(
            "Спасибо за отзыв! Хотите приложить фотографию?\n(или нажмите 'Пропустить' для завершения)",
            reply_markup=get_feedback_skip_keyboard()
        )
        context.user_data["feedback_state"] = FEEDBACK_STATES["WAITING_PHOTO"]

    elif mode == "qa":
        # Handle Q&A
        await handle_question(update, context)

    else:
        # Default: show menu
        await update.message.reply_text(
            "Выберите действие:",
            reply_markup=get_main_menu_keyboard()
        )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages for feedback."""
    mode = context.user_data.get("mode", "qa")
    feedback_state = context.user_data.get("feedback_state")

    if mode == "feedback" and feedback_state == FEEDBACK_STATES["WAITING_PHOTO"]:
        # Get the largest photo
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        
        # Download photo data
        photo_data = await file.download_as_bytearray()
        context.user_data["feedback_photo"] = photo_data
        context.user_data["feedback_photo_filename"] = f"feedback_{photo.file_id}.jpg"
        
        await submit_feedback(update, context)
    else:
        await update.message.reply_text(
            "Фотографии принимаются только в режиме отзывов.",
            reply_markup=get_main_menu_keyboard()
        )


async def handle_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles user questions using the knowledge base."""
    user_question = update.message.text
    chat_id = update.message.chat_id

    logger.info(f"Question from {chat_id}: {user_question}")

    # Try to get collection (reconnect if needed)
    current_collection = get_collection()
    if not current_collection:
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
        results = current_collection.query(
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
        await update.message.reply_text(
            answer,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 В главное меню", callback_data="back_to_menu")
            ]])
        )
        logger.info("Response sent successfully")

    except Exception as e:
        logger.error(f"Error processing question for chat_id {chat_id}: {e}")
        await update.message.reply_text(NOT_FOUND_MESSAGE)


async def submit_feedback(update_or_query, context):
    """Submit feedback to the API."""
    user = update_or_query.from_user if hasattr(update_or_query, 'from_user') else update_or_query.message.from_user
    
    # Prepare feedback data
    feedback_data = {
        "rating": context.user_data.get("feedback_rating"),
        "message_text": context.user_data.get("feedback_text", ""),
        "user_telegram_id": user.id,
        "username": user.username or "",
        "first_name": user.first_name or "",
        "last_name": user.last_name or ""
    }

    # Prepare files if photo exists
    files = None
    if "feedback_photo" in context.user_data:
        # Create BytesIO object from bytearray
        photo_bytes = context.user_data["feedback_photo"]
        photo_io = BytesIO(photo_bytes)
        photo_io.seek(0)  # Reset position to beginning
        
        files = [
            ("images", (
                context.user_data["feedback_photo_filename"],
                photo_io,
                "image/jpeg"
            ))
        ]

    try:
        # Send feedback to API
        headers = {"X-Bot-Token": TELEGRAM_TOKEN}
        response = await http_client.post(
            f"{FEEDBACK_API_URL}/bots/{BOT_ID}/feedbacks",
            data=feedback_data,
            files=files,
            headers=headers
        )

        if response.status_code == 200:
            message = FEEDBACK_THANKS_MESSAGE
        else:
            message = "Произошла ошибка при отправке отзыва. Попробуйте позже."
            logger.error(f"Feedback API error: {response.status_code} - {response.text}")

    except Exception as e:
        message = "Произошла ошибка при отправке отзыва. Попробуйте позже."
        logger.error(f"Error submitting feedback: {e}")

    # Clear feedback data
    context.user_data.clear()

    # Send response
    if hasattr(update_or_query, 'edit_message_text'):
        await update_or_query.edit_message_text(
            message,
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await update_or_query.message.reply_text(
            message,
            reply_markup=get_main_menu_keyboard()
        )


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
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Q&A + Feedback Bot is starting...")
    application.run_polling()


if __name__ == "__main__":
    main() 