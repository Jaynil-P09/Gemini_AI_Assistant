# Gemini Based Voice Assistant
A program that utilises livekit and a Gemini api to create a simple voice assistant which can be modified by adding custom tools or commands, as well as modify the voice assistants personality and voice, which can run either on livekit cloud or inside of a console.

## Installation and Usage:
**1. You will need to start by installing a few libraries, it is recommended to do this inside of a venv**

```ruby
pip install dotenv livekit livekit-agents livekit-plugins-openai livekit-plugins-silero livekit-plugins-google livekit-plugins-noise-cancellationmgoogle-search-results langchain_community python_dotenv duckduckgo-search google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
winget install LiveKit.LiveKitCLI
```
**2. Then connect it to your live kit account which you can make here https://cloud.livekit.io/**
```ruby
lk cloud auth
```
**3. Then on the live kit website go into the settings and click on "API KEYS" and click create an API key in the top right and copy it into a new .env file**
```ruby
#It should look like this right now
LIVEKIT_URL=<Your Live Kit URL>
LIVEKIT_API_KEY=<Your API Key>
LIVEKIT_API_SECRET=<Your API Secret>
```
**4. Go onto Google Cloud(https://cloud.google.com/) and create an account, then create a new project and then go to Google AI Studio and click Create an API Key and connect it to your cloud project, then Copy that API key into your .env file so that it looks like this**
```ruby
#It should look like this right now
LIVEKIT_URL=<Your Live Kit URL>
LIVEKIT_API_KEY=<Your API Key>
LIVEKIT_API_SECRET=<Your API Secret>
GOOGLE_API_KEY=<Your API Key>
```
**5. Then go into the project file and make a file called prompts.py, this is where you will describe what the AI is supposed to do and how it is supposed to act**
```ruby
#Here's mine as an example
AGENT_INSTRUCTION = """
# Persona 
You are a personal Assistant called Quanta with similar function to the AI Jarvis from Iron Man.

# Specifics
- Speak like a classy butler 
- Be sarcastic and witty when speaking to the person you are assisting.
- Use first person when speaking to the user
- If you are asked to do something actknowledge that you will do it and say something like:
  - "Will do, Sir"
  - "Roger Boss"
  or
  - "Check!"
- And after that say what you just done in a small sentence if you have done a task

# Examples
- User: "Hi can you do XYZ for me?"
- Quanta: "Of course sir, as you wish. I will now do the task XYZ for you."
or
- User: "Can you tell me about XYZ?"
- Quanta: "Certainly, Sir. Allow me to enlighten you about XYZ."
"""

SESSION_INSTRUCTION = """
    # Task
    Provide assistance by using the tools that you have access to when needed.
    Also provide information about topics that the user asks about.
    Begin the conversation by saying: " Hi my name is Quanta, your personal assistant, how may I help you today? "
"""
```
**6. Then go into the project file and add a new .py file called agent.py**
```ruby
from dotenv import load_dotenv
from livekit import agents
from livekit.agents import AgentSession, Agent, RoomInputOptions, ChatContext, ChatMessage
from livekit.plugins import (
    noise_cancellation,
)
from livekit.plugins import google
from prompts import AGENT_INSTRUCTION, SESSION_INSTRUCTION
from tools import (
    get_weather, 
    search_web, 
    send_email,
    read_messages,
    search_gmail,
    create_google_calendar_event,
    view_google_calendar,
    delete_google_calendar_event,
    search_google_calendar_events,
    list_google_calendars
)
load_dotenv()
from mem0 import MemoryClient
import json
import sounddevice as sd

try:
    default_input = sd.default.device[0]
    print(f"Using audio input device: {default_input}")
except:
    default_input = 0
    print(f"Using fallback audio device: {default_input}")

#client = MemoryClient(api_key="m0-eSgfxb7z6Ij8XZEW9WfNJd3SiscaD4sHe7FFCLpV")

class Assistant(Agent):
    def __init__(self, user_id: str) -> None:
        super().__init__(
            instructions=AGENT_INSTRUCTION,
            llm=google.beta.realtime.RealtimeModel(
                voice="Aoede",
                temperature=0.8,
            ),
        )
        self.user_id = user_id

async def entrypoint(ctx: agents.JobContext):
    metadata = json.loads(ctx.job.metadata) if ctx.job.metadata else {}
    user_id = metadata.get("user_id", ctx.room.name)

    session = AgentSession()

    await session.start(
        room=ctx.room,
        agent=Assistant(user_id=user_id),
        room_input_options=RoomInputOptions(
            video_enabled=True,
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    await ctx.connect()

    await session.generate_reply(
        instructions=SESSION_INSTRUCTION,
    )

if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
```
**This will give you a basic AI voice assistant with no other tools or functions**
```ruby
**To run it you can do one of two things**
#to run in terminal use 
python agent.py console
#to run in a live-kit playground
python agent.py dev
```

## Adding Tools(Optional)
**If you weren't satisfied witha basic voice assistant like me this is how you can add tools so you can add some custom functionality to your voice assistance**

**1. First create a new tools.py file in your project where you will make all of your tools**

**2. Then go to the Google Cloud project Console for the AI and open it and go to API's & Services and search through and decide which ones you want to turn on**

**3. Then go into OAuth consent screena nd create one for all of your new services and don't forget to turn on access to the email account you want to use**

**4. Then create the tools you want to use you can see mine in the tools.py in this repo**

**5. Then finally to test your new tools change your agent.py to include your new tools**
```ruby
def __init__(self, user_id: str) -> None:
        super().__init__(
            instructions=AGENT_INSTRUCTION,
            llm=google.beta.realtime.RealtimeModel(
                voice="Aoede",
                temperature=0.8,
            ),
            tools=[
            <Your tools>
            ],
        )
        self.user_id = user_id
```
**The first time you use any of the tools it will open a access verification page where you will have to login but only a one-time login as it will be saved in a .pickle file if it is called again**

**Note: The code is from the Livekit Documentation except for the tools which I made**

**If there are any problems please leave a comment on this Repo**
