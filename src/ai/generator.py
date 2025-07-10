import os
import json
import openai
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

from src.bots.models import BotType
from src.ai.knowledge import query_knowledge_base, get_knowledge_base_collection

load_dotenv()

# Initialize OpenAI client
openai_client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Template configuration prompts
QA_TEMPLATE_FILLER_PROMPT = """
You are an expert assistant that configures Telegram Q&A bots. Based on the user requirements and knowledge base content, generate appropriate messages for the bot.

User requirements: "{requirements}"
Knowledge base content: "{knowledge_preview}"

Generate a JSON object with these keys:
1. "start_message": A friendly welcome message that introduces the bot
2. "not_found_message": Message when no answer is found in the knowledge base
3. "rag_system_prompt": System prompt for the AI that tells it how to answer questions based on provided context

Keep messages simple, friendly, and appropriate for the business/service described in the requirements.

Example output:
{{
  "start_message": "Привет! Я помогу ответить на ваши вопросы. Что вас интересует?",
  "not_found_message": "Извините, я не нашел информации по вашему вопросу. Попробуйте переформулировать вопрос.",
  "rag_system_prompt": "Ты полезный помощник. Отвечай на вопросы пользователя на основе предоставленного контекста. Если информации нет в контексте, скажи что не можешь найти эту информацию."
}}
"""

SIMPLE_CHAT_FILLER_PROMPT = """
You are a helpful assistant that configures Telegram bots. Based on the user's high-level requirements, your task is to generate the text content for a simple chat bot.

The user's requirements are: "{requirements}"

Generate a JSON object with the following two keys:
1. "start_message": A friendly welcome message for the /start command that introduces the bot based on the requirements.
2. "chat_system_prompt": A system prompt for the AI model that defines the bot's personality and behavior based on the requirements.

Example output format:
{{
  "start_message": "Hello! I'm your friendly assistant. How can I help you today?",
  "chat_system_prompt": "You are a helpful and friendly assistant. Be concise but informative in your responses."
}}

Now, generate the JSON for the given requirements.
"""

QA_FEEDBACK_TEMPLATE_FILLER_PROMPT = """
You are an expert assistant that configures advanced Telegram Q&A + Feedback bots. Based on the user requirements and knowledge base content, generate appropriate messages for the bot.

This bot combines Q&A functionality with a feedback collection system. Users can ask questions about the knowledge base OR leave feedback with ratings and photos.

User requirements: "{requirements}"
Knowledge base content: "{knowledge_preview}"

Generate a JSON object with these keys:
1. "start_message": A friendly welcome message that introduces BOTH Q&A and feedback features
2. "not_found_message": Message when no answer is found in the knowledge base
3. "rag_system_prompt": System prompt for the AI that tells it how to answer questions based on provided context
4. "feedback_welcome_message": Message that introduces the feedback system when user chooses feedback mode
5. "feedback_thanks_message": Thank you message after feedback is successfully submitted

Keep messages professional, friendly, and appropriate for the business/service described in the requirements.

Example output:
{{
  "start_message": "Добро пожаловать! 🤖 Я могу ответить на ваши вопросы и принять ваш отзыв. Выберите действие в меню ниже.",
  "not_found_message": "Извините, я не нашел информации по вашему вопросу. Попробуйте переформулировать вопрос.",
  "rag_system_prompt": "Ты полезный помощник. Отвечай на вопросы пользователя на основе предоставленного контекста. Если информации нет в контексте, скажи что не можешь найти эту информацию.",
  "feedback_welcome_message": "💬 Мы ценим ваше мнение! Ваш отзыв поможет нам улучшить наш сервис.",
  "feedback_thanks_message": "🙏 Спасибо за ваш отзыв! Мы обязательно его рассмотрим и постараемся стать лучше."
}}
"""


def load_template(template_name: str) -> str:
    """Loads a bot template file from the templates directory."""
    template_path = Path(__file__).parent / "templates" / template_name
    with open(template_path, 'r') as f:
        return f.read()


async def generate_bot_code(bot_id: int, bot_type: BotType, requirements: str, knowledge_base_status: str = None) -> str:
    """
    Generates bot code by filling a template based on the bot_type.
    
    Args:
        bot_id: The bot ID
        bot_type: The type of bot to generate
        requirements: User requirements for the bot
        knowledge_base_status: Status of knowledge base (for Q&A bots)
    
    Returns:
        Generated bot code
    """
    if bot_type == BotType.qa_knowledge_base:
        if knowledge_base_status != "ready":
            raise ValueError("Cannot generate Q&A bot: The knowledge base is not ready.")
        return await _generate_qa_bot_from_template(bot_id, requirements)
    
    elif bot_type == BotType.qa_feedback:
        if knowledge_base_status != "ready":
            raise ValueError("Cannot generate Q&A + Feedback bot: The knowledge base is not ready.")
        return await _generate_qa_feedback_bot_from_template(bot_id, requirements)
    
    elif bot_type == BotType.simple_chat:
        return await _generate_simple_chat_from_template(bot_id, requirements)
    
    else:
        raise NotImplementedError(f"Bot type '{bot_type}' does not have a generator.")


async def _generate_qa_bot_from_template(bot_id: int, requirements: str) -> str:
    """Fills the Q&A bot template with AI-generated content."""
    print(f"Generating Q&A bot for bot_id: {bot_id} using template.")
    
    # 1. Get knowledge base preview for context
    knowledge_preview = await _get_knowledge_base_preview(bot_id)
    
    # 2. Prepare the prompt for the AI
    prompt = QA_TEMPLATE_FILLER_PROMPT.format(
        requirements=requirements,
        knowledge_preview=knowledge_preview
    )

    # 3. Call OpenAI API to get the JSON configuration
    completion = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You are a helpful assistant that only outputs valid JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
    )
    
    try:
        # 4. Parse the JSON response
        ai_config = json.loads(completion.choices[0].message.content)
        print(f"AI Config generated: {list(ai_config.keys())}")
        
        # 5. Load the template file
        template_code = load_template('qa_bot_template.py')

        # 6. Fill the template with AI-generated values (with fallbacks)
        final_code = template_code.replace("{{BOT_ID}}", str(bot_id))
        final_code = final_code.replace("{{START_MESSAGE}}", ai_config.get('start_message', 'Привет! Я ваш помощник. Задавайте вопросы!'))
        final_code = final_code.replace("{{NOT_FOUND_MESSAGE}}", ai_config.get('not_found_message', "Извините, я не нашел информации по вашему вопросу."))
        final_code = final_code.replace("{{RAG_SYSTEM_PROMPT}}", ai_config.get('rag_system_prompt', 'Отвечай на вопросы пользователя на основе предоставленного контекста. Если информации нет в контексте, скажи что не можешь найти эту информацию.'))

        print(f"Successfully generated bot code for bot {bot_id}")
        return final_code

    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing AI response for bot {bot_id}: {e}")
        # Fallback to basic template with default messages
        template_code = load_template('qa_bot_template.py')
        final_code = template_code.replace("{{BOT_ID}}", str(bot_id))
        final_code = final_code.replace("{{START_MESSAGE}}", 'Привет! Я ваш помощник. Задавайте вопросы!')
        final_code = final_code.replace("{{NOT_FOUND_MESSAGE}}", "Извините, я не нашел информации по вашему вопросу.")
        final_code = final_code.replace("{{RAG_SYSTEM_PROMPT}}", 'Отвечай на вопросы пользователя на основе предоставленного контекста. Если информации нет в контексте, скажи что не можешь найти эту информацию.')
        return final_code


async def _generate_simple_chat_from_template(bot_id: int, requirements: str) -> str:
    """Fills the simple chat bot template with AI-generated content."""
    print(f"Generating simple chat bot for bot_id: {bot_id} using template.")
    
    # 1. Prepare the prompt for the AI
    prompt = SIMPLE_CHAT_FILLER_PROMPT.format(requirements=requirements)

    # 2. Call OpenAI API to get the JSON configuration
    completion = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},  # Use JSON mode for reliability
        messages=[
            {"role": "system", "content": "You are a helpful assistant that only outputs valid JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.5,
    )
    
    try:
        # 3. Parse the JSON response
        ai_config = json.loads(completion.choices[0].message.content)
        
        # 4. Load the template file
        template_code = load_template('simple_chat_template.py')

        # 5. Fill the template with the AI-generated values and bot-specific data
        final_code = template_code.replace("{{BOT_ID}}", str(bot_id))
        final_code = final_code.replace("{{START_MESSAGE}}", ai_config['start_message'])
        final_code = final_code.replace("{{CHAT_SYSTEM_PROMPT}}", ai_config['chat_system_prompt'])

        return final_code

    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing AI response for bot {bot_id}: {e}")
        raise ValueError("Failed to generate bot configuration from AI.")


async def _generate_qa_feedback_bot_from_template(bot_id: int, requirements: str) -> str:
    """Fills the Q&A + Feedback bot template with AI-generated content."""
    print(f"Generating Q&A + Feedback bot for bot_id: {bot_id} using template.")
    
    # 1. Get knowledge base preview for context
    knowledge_preview = await _get_knowledge_base_preview(bot_id)
    
    # 2. Prepare the prompt for the AI
    prompt = QA_FEEDBACK_TEMPLATE_FILLER_PROMPT.format(
        requirements=requirements,
        knowledge_preview=knowledge_preview
    )

    # 3. Call OpenAI API to get the JSON configuration
    completion = await openai_client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You are a helpful assistant that only outputs valid JSON."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3,
    )
    
    try:
        # 4. Parse the JSON response
        ai_config = json.loads(completion.choices[0].message.content)
        print(f"AI Config generated for Q&A + Feedback: {list(ai_config.keys())}")
        
        # 5. Load the template file
        template_code = load_template('qa_feedback_bot_template.py')

        # 6. Fill the template with AI-generated values (with fallbacks)
        final_code = template_code.replace("{{BOT_ID}}", str(bot_id))
        final_code = final_code.replace("{{START_MESSAGE}}", ai_config.get('start_message', 'Добро пожаловать! 🤖 Я могу ответить на ваши вопросы и принять ваш отзыв. Выберите действие в меню ниже.'))
        final_code = final_code.replace("{{NOT_FOUND_MESSAGE}}", ai_config.get('not_found_message', "Извините, я не нашел информации по вашему вопросу."))
        final_code = final_code.replace("{{RAG_SYSTEM_PROMPT}}", ai_config.get('rag_system_prompt', 'Отвечай на вопросы пользователя на основе предоставленного контекста. Если информации нет в контексте, скажи что не можешь найти эту информацию.'))
        final_code = final_code.replace("{{FEEDBACK_WELCOME_MESSAGE}}", ai_config.get('feedback_welcome_message', '💬 Мы ценим ваше мнение! Ваш отзыв поможет нам улучшить наш сервис.'))
        final_code = final_code.replace("{{FEEDBACK_THANKS_MESSAGE}}", ai_config.get('feedback_thanks_message', '🙏 Спасибо за ваш отзыв! Мы обязательно его рассмотрим и постараемся стать лучше.'))

        print(f"Successfully generated Q&A + Feedback bot code for bot {bot_id}")
        return final_code

    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error parsing AI response for Q&A + Feedback bot {bot_id}: {e}")
        # Fallback to basic template with default messages
        template_code = load_template('qa_feedback_bot_template.py')
        final_code = template_code.replace("{{BOT_ID}}", str(bot_id))
        final_code = final_code.replace("{{START_MESSAGE}}", 'Добро пожаловать! 🤖 Я могу ответить на ваши вопросы и принять ваш отзыв. Выберите действие в меню ниже.')
        final_code = final_code.replace("{{NOT_FOUND_MESSAGE}}", "Извините, я не нашел информации по вашему вопросу.")
        final_code = final_code.replace("{{RAG_SYSTEM_PROMPT}}", 'Отвечай на вопросы пользователя на основе предоставленного контекста. Если информации нет в контексте, скажи что не можешь найти эту информацию.')
        final_code = final_code.replace("{{FEEDBACK_WELCOME_MESSAGE}}", '💬 Мы ценим ваше мнение! Ваш отзыв поможет нам улучшить наш сервис.')
        final_code = final_code.replace("{{FEEDBACK_THANKS_MESSAGE}}", '🙏 Спасибо за ваш отзыв! Мы обязательно его рассмотрим и постараемся стать лучше.')
        return final_code


async def _get_knowledge_base_preview(bot_id: int) -> str:
    """Get a comprehensive preview of the knowledge base content for company analysis."""
    try:
        collection = get_knowledge_base_collection(bot_id)
        
        # Search for multiple company-related queries to get comprehensive info
        search_queries = [
            "company about us overview",  # Basic company info
            "name founded team",          # Company name and team info  
            "what we do services business",  # Business description
            "contact email support",      # Contact information
            "mission vision values",      # Company culture
            "products solutions"          # What they offer
        ]
        
        all_chunks = []
        seen_chunks = set()  # Avoid duplicates
        
        for query in search_queries:
            try:
                results = collection.query(
                    query_texts=[query],
                    n_results=3  # Get top 3 for each query
                )
                
                if results['documents'] and results['documents'][0]:
                    for chunk in results['documents'][0]:
                        # Only add unique chunks
                        if chunk not in seen_chunks and len(chunk.strip()) > 50:
                            all_chunks.append(chunk)
                            seen_chunks.add(chunk)
                            
            except Exception as e:
                print(f"Error with query '{query}': {e}")
                continue
        
        # If we didn't get enough content, get some random chunks
        if len(all_chunks) < 3:
            try:
                random_results = collection.query(
                    query_texts=[""],  # Empty query to get random chunks
                    n_results=5
                )
                if random_results['documents'] and random_results['documents'][0]:
                    for chunk in random_results['documents'][0][:3]:
                        if chunk not in seen_chunks:
                            all_chunks.append(chunk)
                            seen_chunks.add(chunk)
            except:
                pass
        
        if all_chunks:
            # Join chunks with clear separators and limit length
            preview = "\n\n---DOCUMENT SECTION---\n\n".join(all_chunks[:6])  # Max 6 chunks
            
            # Limit to reasonable size but allow more than before
            if len(preview) > 2500:
                preview = preview[:2500] + "...\n\n[Content truncated - more documents available in knowledge base]"
                
            print(f"Knowledge base preview generated: {len(all_chunks)} chunks, {len(preview)} characters")
            return preview
        else:
            return "No knowledge base content available for analysis"
            
    except Exception as e:
        print(f"Error getting knowledge base preview for bot {bot_id}: {e}")
        return "Knowledge base preview unavailable - please check if PDF was processed correctly"
