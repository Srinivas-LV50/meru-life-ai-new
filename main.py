from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from nemoguardrails import RailsConfig, LLMRails
from langchain_groq import ChatGroq
from nemoguardrails.llm.providers import register_llm_provider
from fastapi.middleware.cors import CORSMiddleware
import os

os.environ.setdefault("GROQ_API_KEY", "")

# Initialize FastAPI
app = FastAPI()

# Add CORS middleware to allow requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this list to restrict domains in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register Groq as an LLM provider
register_llm_provider("groq", ChatGroq)

# Load NeMo Guardrails configuration
config = RailsConfig.from_path("./config")
rails = LLMRails(config)

# Define Companion Profiles
COMPANION_PROFILES = {
    "1": {
        "personality": "Energetic, light-hearted, and always positive",
        "role": "The uplifting friend who brings joy and optimism",
        "prompt": (
            "You are an energetic, lighthearted, and always-positive companion. Your purpose is to uplift and cheer up the senior. "
            "You joke, tell stories, and make them smile.\n"
            "Speaking Style: Friendly, casual, full of enthusiasm.\n"
            "Preferred Topics: Funny anecdotes, simple joys, optimism, hobbies.\n"
            "Memory Use: Remind users of things they enjoyed.\n"
        ),
    },
    "2": {
        "personality": "Patient, empathetic, and great at listening",
        "role": "A non-judgmental confidante",
        "prompt": (
            "You are a patient, non-judgmental, and deeply empathetic companion. You listen actively and offer supportive responses.\n"
            "Speaking Style: Gentle, reassuring, minimal interruptions.\n"
            "Preferred Topics: User-led conversations, emotions, personal stories.\n"
            "Memory Use: Acknowledge previous discussions and build on them.\n"
        ),
    }
}

# Define Request Model
class ChatRequest(BaseModel):
    user_id: str
    companion_id: str
    conversation: list[dict]  # Example: [{"role": "user", "content": "Hello!"}]
    question: str  # Direct user question

@app.post("/chat")
async def chat_with_guardrails(request: ChatRequest):
    try:
        # Ensure a valid companion_id is provided
        if request.companion_id not in COMPANION_PROFILES:
            raise HTTPException(status_code=400, detail="Invalid companion_id. Choose between '1' and '2'.")

        # Get the specific companion profile
        companion_profile = COMPANION_PROFILES[request.companion_id]

        # Construct messages with context
        messages = [{"role": "system", "content": companion_profile["prompt"]}]

        # Append previous conversation history
        messages.extend(request.conversation)

        # Append the latest user query
        messages.append({"role": "user", "content": request.question})

        # Generate response using NeMo Guardrails & Groq
        response = await rails.generate_async(messages=messages)

        return {
            "user_id": request.user_id,
            "companion_id": request.companion_id,
            "response": response["content"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
