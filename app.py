import os
import asyncio
from livekit import agents, rtc
from dotenv import load_dotenv
from typing import Optional
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

class AICallingAgent:
    def __init__(self):
        self.chat_history = []
        
    async def on_participant_connected(self, participant: rtc.RemoteParticipant):
        logger.info(f"Participant connected: {participant.identity}")
        
        @participant.on("track_published")
        async def on_track_published(publication: rtc.RemoteTrackPublication):
            if publication.kind == rtc.TrackKind.KIND_AUDIO:
                logger.info(f"Audio track published by {participant.identity}")
                track = await publication.track
                await self.handle_audio_track(track, participant.identity)
    
    async def handle_audio_track(self, track: rtc.AudioTrack, participant_id: str):
        # Set up audio stream
        stream = rtc.AudioStream(track)
        
        # Initialize speech recognition
        stt = agents.speech.create_speech_to_text()
        tts = agents.speech.create_text_to_speech()
        
        # Process audio chunks
        async for audio_frame_event in stream:
            # Transcribe speech
            transcription = await stt.process_audio(
                audio_frame_event.frame,
                sample_rate=audio_frame_event.sample_rate,
                num_channels=audio_frame_event.num_channels
            )
            
            if transcription.text:
                logger.info(f"User said: {transcription.text}")
                self.chat_history.append({
                    "from": participant_id,
                    "text": transcription.text,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Generate AI response
                response = await self.generate_response(transcription.text)
                
                # Speak response
                self.chat_history.append({
                    "from": "AI Agent",
                    "text": response,
                    "timestamp": datetime.now().isoformat()
                })
                
                # Synthesize speech
                tts_stream = await tts.synthesize(response)
                await track.room.local_participant.publish_audio(tts_stream)
    
    async def generate_response(self, text: str) -> str:
        """Simple response logic - extend with your AI/NLP"""
        text = text.lower()
        
        if any(word in text for word in ["hello", "hi", "hey"]):
            return "Hello! How can I help you today?"
        elif any(word in text for word in ["help", "support"]):
            return "I'd be happy to help. Can you please describe your issue?"
        elif any(word in text for word in ["thank", "thanks"]):
            return "You're welcome! Is there anything else I can help with?"
        else:
            return "I understand. Please tell me more about your request."

async def run_agent(room: rtc.Room):
    agent = AICallingAgent()
    
    @room.on("participant_connected")
    async def on_participant_connected(participant: rtc.RemoteParticipant):
        await agent.on_participant_connected(participant)
    
    logger.info("AI calling agent is ready")

async def main():
    # Connect to LiveKit server
    room = rtc.Room()
    
    try:
        await room.connect(
            os.getenv("LIVEKIT_URL"),
            os.getenv("LIVEKIT_API_KEY"),
            os.getenv("LIVEKIT_API_SECRET"),
            identity="ai-agent"
        )
        
        await run_agent(room)
        
        # Keep the agent running
        while True:
            await asyncio.sleep(1)
            
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        await room.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
