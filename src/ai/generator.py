import os
import openai
from dotenv import load_dotenv
import asyncio

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

Additional requirements:
1. Use async/await everywhere.
2. Read `BOT_TOKEN` and `OPENAI_API_KEY` from environment variables.
3. Initialize an `openai.AsyncOpenAI` client in the global scope, not inside a handler.
4. Implement a `/start` handler with a greeting.
5. Implement a default message handler that:
   a) Takes any incoming text message.
   b) Uses the global OpenAI client to call the chat completions API:
      ```python
      response = await client.chat.completions.create(
          model="gpt-4o-mini",
          messages=[
              {{"role": "system", "content": "You are a helpful assistant."}},
              {{"role": "user", "content": update.message.text}}
          ],
          temperature=0.7,
      )
      answer = response.choices[0].message.content
      ```
   c) Sends `answer` back to the user.
6. Include all necessary imports: `import openai`, `import os`, `from telegram import Update`, `from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes`.
7. Wrap startup in a synchronous `main()` function that builds the Application, adds handlers, and calls `application.run_polling()`.
8. The `main` function should be called directly from the `if __name__ == '__main__':` block.

Return ONLY the final, runnable Python code—никаких пояснений и никаких markdown-фрейм.
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

if __name__ == '__main__':
    asyncio.run(AIBotGenerator().generate_bot_code(""))
