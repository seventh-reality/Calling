import { Room, LocalParticipant, RemoteParticipant } from 'livekit-client';

const agentCalls = {
  currentCall: null,
  callHistory: [],
  
  async startOutboundCall(participantId) {
    try {
      const room = new Room();
      await room.connect('wss://your-livekit-server', 'participant-' + participantId);
      
      this.currentCall = {
        room,
        participantId,
        startTime: new Date(),
        status: 'connecting'
      };
      
      // Set up event listeners
      room.on('participantConnected', participant => {
        if (participant.identity === 'ai-agent') {
          this.currentCall.status = 'connected';
          this.updateUI();
        }
      });
      
      room.on('disconnected', () => {
        this.endCurrentCall();
      });
      
      // Publish local audio
      await room.localParticipant.enableMicrophone();
      
      this.callHistory.push({
        type: 'outbound',
        participantId,
        startTime: this.currentCall.startTime,
        status: 'initiated'
      });
      
      this.updateUI();
      
    } catch (error) {
      console.error('Call failed:', error);
      this.currentCall.status = 'failed';
      this.updateUI();
    }
  },
  
  endCurrentCall() {
    if (this.currentCall) {
      this.currentCall.room.disconnect();
      
      const call = this.callHistory.find(c => 
        c.participantId === this.currentCall.participantId && 
        c.startTime === this.currentCall.startTime
      );
      
      if (call) {
        call.endTime = new Date();
        call.duration = call.endTime - call.startTime;
        call.status = 'completed';
      }
      
      this.currentCall = null;
      this.updateUI();
    }
  },
  
  updateUI() {
    // Update your UI here
    console.log('Call status updated:', this.currentCall);
  }
};

// UI Event Listeners
document.getElementById('startCallBtn').addEventListener('click', () => {
  const participantId = document.getElementById('participantId').value;
  if (participantId) {
    agentCalls.startOutboundCall(participantId);
  }
});

document.getElementById('endCallBtn').addEventListener('click', () => {
  agentCalls.endCurrentCall();
});
