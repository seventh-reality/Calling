from flask import Flask, request, render_template, jsonify
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse
import os
from dotenv import load_dotenv
import pandas as pd
import time
from threading import Thread
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = Flask(__name__)

# Initialize Twilio client
account_sid = os.getenv('TWILIO_ACCOUNT_SID')
auth_token = os.getenv('TWILIO_AUTH_TOKEN')
twilio_number = os.getenv('TWILIO_PHONE_NUMBER')

if not all([account_sid, auth_token, twilio_number]):
    logger.error("Missing Twilio credentials in environment variables")
    raise ValueError("Missing Twilio credentials")

client = Client(account_sid, auth_token)

# Global variables for call tracking
call_queue = []
active_calls = {}
call_history = []

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    try:
        # Read the file
        if file.filename.endswith('.csv'):
            df = pd.read_csv(file)
        elif file.filename.endswith(('.xlsx', '.xls')):
            df = pd.read_excel(file)
        else:
            return jsonify({'error': 'Unsupported file format. Please upload CSV or Excel.'}), 400
        
        # Extract phone numbers (try common column names)
        phone_col = None
        for col in df.columns:
            if 'phone' in col.lower() or 'number' in col.lower():
                phone_col = col
                break
        
        if not phone_col:
            return jsonify({'error': 'No phone number column found. Please name your column "phone" or "number".'}), 400
        
        global call_queue
        call_queue = df[phone_col].astype(str).str.strip().tolist()
        
        # Start calling process in background
        Thread(target=process_call_queue, daemon=True).start()
        
        return jsonify({
            'message': f'Successfully uploaded {len(call_queue)} numbers',
            'total_numbers': len(call_queue)
        })
    
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        return jsonify({'error': f'Error processing file: {str(e)}'}), 500

@app.route('/call-status')
def get_call_status():
    completed = len([v for v in active_calls.values() if v == 'completed'])
    failed = len([v for v in active_calls.values() if v == 'failed'])
    
    return jsonify({
        'total': len(call_queue),
        'completed': completed,
        'failed': failed,
        'active': len(active_calls) - completed - failed,
        'history': call_history[-10:]  # Show last 10 calls
    })

@app.route('/call-handler', methods=['POST'])
def call_handler():
    """Handle incoming call from Twilio (when recipient answers)"""
    resp = VoiceResponse()
    
    # Get call details
    called_number = request.form.get('To', '')
    call_sid = request.form.get('CallSid', '')
    
    # Mark call as active
    active_calls[call_sid] = 'in-progress'
    call_history.append({
        'number': called_number,
        'status': 'in-progress',
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    })
    
    # AI Agent logic - customize this part
    resp.say("Hello, this is an AI calling agent. Thank you for your time today.", 
             voice='Polly.Joanna')
    
    # Add gather to collect input
    gather = resp.gather(
        input='speech',
        action='/process-speech',
        method='POST',
        speechTimeout='auto'
    )
    gather.say("How can I help you today? Please speak after the tone.")
    
    return str(resp)

@app.route('/process-speech', methods=['POST'])
def process_speech():
    """Process speech input from the call"""
    resp = VoiceResponse()
    speech_result = request.form.get('SpeechResult', '')
    
    # Simple response logic - extend this with your AI/NLP
    if any(word in speech_result.lower() for word in ['help', 'support', 'issue']):
        resp.say("I understand you need help. Let me connect you to a support representative.")
        # Here you could add <Dial> to transfer to a human
    else:
        resp.say("Thank you for your response. Have a great day!")
    
    return str(resp)

@app.route('/call-status-callback', methods=['POST'])
def call_status_callback():
    """Callback for call status updates"""
    call_sid = request.form.get('CallSid', '')
    status = request.form.get('CallStatus', '')
    number = request.form.get('To', '')
    
    # Update our tracking
    active_calls[call_sid] = status
    call_history.append({
        'number': number,
        'status': status,
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
    })
    
    return '', 200

def process_call_queue():
    """Process the call queue and initiate calls"""
    global call_queue, active_calls
    
    for number in call_queue:
        try:
            # Clean the number
            number = ''.join(c for c in number if c.isdigit() or c == '+')
            if not number:
                continue
                
            # Make the call
            call = client.calls.create(
                twiml=f'<Response><Say>Connecting you to our AI agent.</Say></Response>',
                to=number,
                from_=twilio_number,
                status_callback=url_for('call_status_callback', _external=True),
                status_callback_event=['initiated', 'ringing', 'answered', 'completed', 'failed']
            )
            
            # Track the call
            active_calls[call.sid] = 'initiated'
            call_history.append({
                'number': number,
                'status': 'initiated',
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            })
            
            # Add delay between calls (adjust as needed)
            time.sleep(3)
            
        except Exception as e:
            logger.error(f"Error calling {number}: {str(e)}")
            call_history.append({
                'number': number,
                'status': 'failed',
                'error': str(e),
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            })
            continue
            @app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400
    
    file = request.files['file']
    
    # Check if file is empty
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Check file extension
    allowed_extensions = {'csv', 'xlsx', 'xls'}
    if not ('.' in file.filename and 
            file.filename.rsplit('.', 1)[1].lower() in allowed_extensions):
        return jsonify({
            'error': 'Invalid file type. Please upload CSV or Excel files only.',
            'allowed_types': list(allowed_extensions)
        }), 400
    
    try:
        # Read the file based on extension
        if file.filename.lower().endswith('.csv'):
            # For CSV, try different encodings if needed
            try:
                df = pd.read_csv(file)
            except UnicodeDecodeError:
                file.stream.seek(0)  # Reset file pointer
                df = pd.read_csv(file, encoding='latin1')
        else:  # Excel files
            df = pd.read_excel(file)
        
        # Find phone number column (case insensitive)
        phone_col = None
        possible_columns = ['phone', 'number', 'phonenumber', 'mobile', 'contact']
        
        for col in df.columns:
            col_lower = col.strip().lower()
            for possible in possible_columns:
                if possible in col_lower:
                    phone_col = col
                    break
            if phone_col:
                break
        
        if not phone_col:
            return jsonify({
                'error': 'No phone number column found. Please include a column with one of these names:',
                'suggested_columns': possible_columns,
                'found_columns': list(df.columns)
            }), 400
        
        # Clean and validate phone numbers
        df[phone_col] = df[phone_col].astype(str).str.strip()
        df = df[df[phone_col].str.match(r'^\+?[\d\s\-\(\)]{7,}$')]  # Basic phone number validation
        
        if len(df) == 0:
            return jsonify({
                'error': 'No valid phone numbers found after validation',
                'validation_regex': r'^\+?[\d\s\-\(\)]{7,}$'
            }), 400
        
        global call_queue
        call_queue = df[phone_col].tolist()
        
        # Start calling process in background
        Thread(target=process_call_queue, daemon=True).start()
        
        return jsonify({
            'message': f'Successfully processed {len(call_queue)} valid phone numbers',
            'total_numbers': len(call_queue),
            'sample_numbers': call_queue[:3]  # Show first 3 as sample
        })
    
    except pd.errors.EmptyDataError:
        return jsonify({'error': 'The file is empty'}), 400
    except pd.errors.ParserError:
        return jsonify({'error': 'Error parsing the file. Please check the file format.'}), 400
    except Exception as e:
        logger.error(f"File processing error: {str(e)}", exc_info=True)
        return jsonify({
            'error': f'An error occurred while processing the file: {str(e)}',
            'type': type(e).__name__
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
    def process_call_queue():
    """Process the call queue and initiate calls"""
    global call_queue, active_calls
    
    for number in call_queue:
        try:
            # Clean the number - keep only digits and +
            cleaned_number = ''.join(c for c in str(number) if c.isdigit() or c == '+')
            
            # Add country code if missing (example for US)
            if not cleaned_number.startswith('+'):
                cleaned_number = f'+1{cleaned_number}'  # Default to US
                logger.warning(f"Added default country code to {number}")
            
            # Validate E.164 format
            if not re.match(r'^\+\d{10,15}$', cleaned_number):
                logger.error(f"Invalid number format: {cleaned_number}")
                continue
                
            # Make the call
            call = client.calls.create(
                twiml=f'<Response><Say>Hello, this is an AI calling agent.</Say></Response>',
                to=cleaned_number,
                from_=twilio_number,
                status_callback=url_for('call_status_callback', _external=True),
                status_callback_event=['initiated', 'ringing', 'answered', 'completed', 'failed', 'busy', 'no-answer']
            )
            
            # Track the call
            active_calls[call.sid] = 'initiated'
            call_history.append({
                'number': cleaned_number,
                'status': 'initiated',
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            })
            
            # Add delay between calls (compliance friendly)
            time.sleep(5)  # 5 seconds between calls
            
        except Exception as e:
            logger.error(f"Error calling {number}: {str(e)}")
            call_history.append({
                'number': number,
                'status': 'failed',
                'error': str(e),
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            })
            continue
