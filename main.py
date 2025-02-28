from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from nemoguardrails import RailsConfig, LLMRails
from langchain_groq import ChatGroq
from nemoguardrails.llm.providers import register_llm_provider
from mangum import Mangum
import os

os.environ["GROQ_API_KEY"] = ""
# Initialize FastAPI
app = FastAPI()

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
            "Example Phrasing:\n"
            "\"Oh wow, that’s fantastic! What a great way to start the day!\"\n"
            "\"You know what always makes me smile? A good joke! Want to hear one?\""
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
            "Example Phrasing:\n"
            "\"That must have been difficult. Do you want to talk more about it?\"\n"
            "\"I remember you telling me about your childhood home. How did it feel living there?\""
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
        print(request)
        # Get the specific companion profile
        companion_profile = COMPANION_PROFILES[request.companion_id]

        # Generate conversation summary from history
        conversation_history = "\n".join([f"{msg['role'].capitalize()}: {msg['content']}" for msg in request.conversation])
        Instruction= "If the conversation history is  present try to answer the question always keeping the conversation histoy as context below is the conversation history"
        summary_prompt = f"Previous conversation:\n{conversation_history}\n\n" if conversation_history else ""
        print("conversation_history")
        print(conversation_history)
        messages=[]
        # Define system-level prompt for selected companion
        messages.append({"role": "system","content": "This is the profile of the person that you are interacting with " + companion_profile["prompt"]+ Instruction+ conversation_history})
      
        # Construct messages with system prompt and conversation history
        #messages = [system_prompt] + request.conversation if not request.conversation or request.conversation[0]["role"] != "system" else request.conversation
        
        # Append the user's direct question as the latest message
        messages.append({"role": "user", "content": request.question})
        print(messages)
        # Generate response using NeMo Guardrails & Groq
        #response = await rails.llms.invoke(messages)
        response = await rails.generate_async(messages=messages)

        # Return JSON response with user_id and chosen companion
        return {
            "user_id": request.user_id,
            "companion_id": request.companion_id,
            "response": response["content"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
handler = Mangum(app)
