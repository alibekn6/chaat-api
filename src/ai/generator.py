import os
import openai
from dotenv import load_dotenv

load_dotenv()

# Ensure the OpenAI API key is set as an environment variable
# OPENAI_API_KEY="your-api-key-here"

class AIBotGenerator:
    def __init__(self, api_key: str = os.getenv("OPENAI_API_KEY")):
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set.")
        self.client = openai.AsyncOpenAI(api_key=api_key)

    async def generate_bot_code(self, requirements: str) -> str:
        prompt = f"""
Create a simple Telegram bot in Python using the python-telegram-bot library, version 20+.

Requirements: {requirements}

The code must:
1. Use async/await.
2. Get the bot token from the environment variable os.environ['BOT_TOKEN'].
3. Have a /start command with a greeting.
4. Be ready to run as a standalone script.
5. Include a main() function for startup.

Example Structure:
```python
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello!")

def main():
    token = os.environ.get('BOT_TOKEN')
    if not token:
        raise ValueError("No BOT_TOKEN found in environment variables")
        
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    
    # Run the bot until the user presses Ctrl-C
    app.run_polling()

if __name__ == '__main__':
    main()
```
Return only the final, complete Python code without any explanations or markdown formatting.
"""
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=2000,
        )

        # Extract the code from the response, removing markdown fences if present
        content = response.choices[0].message.content
        if content.strip().startswith("```python"):
            content = content.strip()[9:].strip()
            if content.endswith("```"):
                content = content[:-3].strip()
        
        return content
