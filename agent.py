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

#Get the audio device it will use
try:
    default_input = sd.default.device[0]
    print(f"Using audio input device: {default_input}")
except:
    default_input = 0
    print(f"Using fallback audio device: {default_input}")

#Defining the AI agent
class Assistant(Agent):
    def __init__(self, user_id: str) -> None:
        super().__init__(
            #The AI instructions and voice setting
            instructions=AGENT_INSTRUCTION,
            llm=google.beta.realtime.RealtimeModel(
                voice="Aoede",
                temperature=0.8,
            ),
            #Tools list
            tools=[
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
            ],
        )
        self.user_id = user_id

#Connect to Live Kit servers to either access in a playground or the console
async def entrypoint(ctx: agents.JobContext):
    metadata = json.loads(ctx.job.metadata) if ctx.job.metadata else {}
    user_id = metadata.get("user_id", ctx.room.name)

    session = AgentSession()

    await session.start(
        room=ctx.room,
        agent=Assistant(user_id=user_id),
        room_input_options=RoomInputOptions(
            #Turn video on for the live kit playground if it is used
            video_enabled=True,
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    await ctx.connect()

    #Give the instructions from prompts
    await session.generate_reply(
        instructions=SESSION_INSTRUCTION,
    )
#Initialise the room
if __name__ == "__main__":
    agents.cli.run_app(agents.WorkerOptions(entrypoint_fnc=entrypoint))
