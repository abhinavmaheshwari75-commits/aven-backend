import asyncio
import json
import os
from database import add_long_term_memory
from dotenv import load_dotenv
from groq import Groq

load_dotenv()


def _get_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print(
            "[MEMORY EXTRACTION ERROR] GROQ_API_KEY missing from environment"
            " or .env file."
        )
        return None
    return Groq(api_key=api_key)


async def extract_memories_async(user_message: str, assistant_response: str):
    """Extracts key user facts asynchronously and persists them to long_term_memories."""

    def _extract():
        client = _get_client()
        if not client:
            return

        prompt = f"""
Extract key facts, preferences, or personal details about the user from this conversation turn.
User: {user_message}
Assistant: {assistant_response}

Return ONLY a JSON array of strings containing discrete factual statements. If no new personal fact is disclosed, return [].
Example output: ["User prefers Python for AI development.", "User is building an assistant named Aven."]
        """
        try:
            res = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            text = res.choices[0].message.content.strip()
            if text.startswith("```json"):
                text = text.replace("```json", "").replace("```", "").strip()
            facts = json.loads(text)
            if isinstance(facts, list):
                for fact in facts:
                    if isinstance(fact, str) and fact.strip():
                        add_long_term_memory(fact.strip())
        except Exception as e:
            print(f"[MEMORY EXTRACTION ERROR] {e}")

    await asyncio.to_thread(_extract)