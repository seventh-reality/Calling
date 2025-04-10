from flask import Flask, request, render_template, redirect, url_for
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
import os
from dotenv import load_dotenv
import pandas as pd
import time
from threading import Thread

load_dotenv()

app = Flask(__name__)

# Initialize Twilio client
client = Client(os.getenv('TWILIO_ACCOUNT_SID'), os.getenv('TWILIO_AUTH_TOKEN'))
twilio_number = os.getenv('TWILIO_PHONE_NUMBER')

# Global variable to store numbers and call status
call_queue = []
active_calls = {}

@app.route('/')
def index():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return redirect(request.url)
    
    file = request.files['file']
    if file.filename == '':
        return redirect(request.url)
    
    if file:
        # Read the file (assuming CSV or Excel with phone numbers)
        try:
            if file.filename.endswith('.csv'):
                df = pd.read_csv(file)
            elif file.filename.endswith('.xlsx'):
                df = pd.read_excel(file)
            else:
                return "Unsupported file format", 400
            
            # Assuming phone numbers are in a column named 'phone'
            global call_queue
            call_queue = df['phone'].astype(str).tolist()
            
            # Start calling process in background
            Thread(target=process_call_queue).start()
            
            return render_template('status.html', total_calls=len(call_queue), completed_calls=0)
        except Exception as e:
            return f"Error processing file: {str(e)}", 400

@app.route('/status')
def status():
    completed = len([v for v in active_calls.values() if v == 'completed'])
    return {
        'total': len(call_queue),
        'completed': completed,
        'active': len(active_calls) - completed
    }

@app.route('/call_handler', methods=['POST'])
def call_handler():
    """Handle incoming call from Twilio (when recipient answers)"""
    resp = VoiceResponse()
    
    # Get the called number
    called_number = request.form['To']
    
    # Mark call as active in our tracking
    call_sid = request.form['CallSid']
    active_calls[call_sid] = 'in-progress'
    
    # AI Agent logic - customize this part
    resp.say("Hello, this is an AI calling agent. How can I help you today?", voice='Polly.Joanna')
    
    # You can add more interactive voice response (IVR) logic here
    # For example, gather input, transfer calls, etc.
    
    return str(resp)

@app.route('/call_status', methods=['POST'])
def call_status():
    """Callback for call status updates"""
    call_sid = request.form['CallSid']
    status = request.form['CallStatus']
    
    # Update our tracking
    if status in ['completed', 'failed', 'busy', 'no-answer']:
        active_calls[call_sid] = 'completed'
    
    return '', 200

def process_call_queue():
    """Process the call queue and initiate calls"""
    global call_queue, active_calls
    
    for number in call_queue:
        try:
            # Make the call
            call = client.calls.create(
                twiml=f'<Response><Say>Hello, this is an AI calling agent.</Say></Response>',
                to=number,
                from_=twilio_number,
                status_callback=url_for('call_status', _external=True),
                status_callback_event=['initiated', 'ringing', 'answered', 'completed']
            )
            
            # Track the call
            active_calls[call.sid] = 'initiated'
            
            # Add delay between calls (adjust as needed)
            time.sleep(5)
            
        except Exception as e:
            print(f"Error calling {number}: {str(e)}")
            continue

if __name__ == '__main__':
    app.run(debug=True, port=5000)
