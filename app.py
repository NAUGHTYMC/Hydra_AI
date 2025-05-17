# app.py
from flask import Flask, render_template, request, jsonify, session
from openai import OpenAI
import os
from dotenv import load_dotenv
import base64
import datetime
import logging
import secrets
import json
import time
from flask_session import Session

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

app = Flask(__name__)
# Configure server-side session
app.config['SECRET_KEY'] = os.environ('SECRET_KEY', secrets.token_hex(16))
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_PERMANENT'] = True
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(days=1)
Session(app)

# App configuration
NAME = os.environ("TRADER_NAME", "Hydra")
ANALYSIS_MODEL = os.environ("ANALYSIS_MODEL", "meta-llama/llama-4-maverick:free")
IMAGE_MODEL = os.environ("IMAGE_MODEL", "meta-llama/llama-4-maverick:free")
MAX_HISTORY = int(os.environ("MAX_HISTORY", 10))  # Maximum conversation history to maintain

# Initialize OpenAI client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ("OPENROUTER_API_KEY"),
)

def get_system_prompt():
    """Generate the system prompt with current date and time"""
    return f"""You are Shadow, the AI trading companion of {NAME}, 
    the world's premier stock trader. Your capabilities include:
    - Real-time technical analysis of global markets
    - Precise entry/exit timing with price targets
    - Advanced chart pattern recognition
    - Multi-timeframe analysis (1m to monthly)
    - Volume analysis and order flow interpretation
    - Risk-reward ratio optimization
    - Sentiment analysis integration
    
    Current Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    
    Always respond with:
    - Precise price levels
    - Exact timestamps for entries/exits
    - Clear stop-loss and take-profit levels
    - Confidence percentage for each trade idea
    - Technical rationale (RSI, MACD, Fibonacci, etc.)
    
    If you are analyzing a chart image, provide detailed observations about visible patterns, 
    trendlines, support/resistance levels, and key indicators visible in the chart."""

def initialize_session():
    """Initialize session variables if not already set"""
    if 'conversation_history' not in session:
        session['conversation_history'] = []
    if 'last_interaction' not in session:
        session['last_interaction'] = time.time()

def analyze_command(command, image_data=None):
    """Process user commands and generate AI responses"""
    try:
        # Initialize session
        initialize_session()
        
        # Update last interaction time
        session['last_interaction'] = time.time()
        
        # Prepare conversation history for context
        messages = [{"role": "system", "content": get_system_prompt()}]
        
        # Add conversation history for context (limited to maintain context)
        for msg in session['conversation_history'][-MAX_HISTORY:]:
            messages.append(msg)
        
        # Add current user message
        user_message = {"role": "user", "content": command}
        
        # Handle image if provided
        if image_data:
            base64_image = base64.b64encode(image_data.read()).decode('utf-8')
            user_message = {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Analyze this trading chart: {command}"},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                    },
                ],
            }
        
        messages.append(user_message)
        
        # Log the request (excluding image data for brevity)
        logger.info(f"Processing request: {command[:50]}{'...' if len(command) > 50 else ''}")
        
        # Call the API
        start_time = time.time()
        response = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": os.environ("SITE_URL", "http://localhost:5000"),
                "X-Title": os.environ("SITE_NAME", "Hydra Trading System"),
            },
            model=IMAGE_MODEL if image_data else ANALYSIS_MODEL,
            messages=messages,
            temperature=0.2,
            max_tokens=800  # Increased token limit for more detailed responses
        )
        
        # Log API response time
        logger.info(f"API response time: {time.time() - start_time:.2f}s")
        
        # Extract response content
        ai_response = response.choices[0].message.content
        
        # Update conversation history
        session['conversation_history'].append(user_message)
        session['conversation_history'].append({"role": "assistant", "content": ai_response})
        session.modified = True
        
        return ai_response
        
    except Exception as e:
        logger.error(f"Error in analyze_command: {str(e)}", exc_info=True)
        return f"I encountered an issue processing your request. Please try again. Error details: {str(e)}"

@app.route('/')
def index():
    """Render the main application page"""
    return render_template('index.html', trader_name=NAME)

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat requests with or without images"""
    try:
        user_input = request.form.get('message', '')
        image_file = request.files.get('image')
        
        # Validate input
        if not user_input and not image_file:
            return jsonify({'error': 'No message or image provided'}), 400
        
        if image_file:
            # Process with image analysis
            response = analyze_command(user_input, image_file)
        else:
            # Process text-only analysis
            response = analyze_command(user_input)
        
        return jsonify({'response': response})
    
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}", exc_info=True)
        return jsonify({'error': f"Server error: {str(e)}"}), 500

@app.route('/clear_history', methods=['POST'])
def clear_history():
    """Clear conversation history"""
    try:
        if 'conversation_history' in session:
            session['conversation_history'] = []
            session.modified = True
        return jsonify({'success': True, 'message': 'Conversation history cleared'})
    except Exception as e:
        logger.error(f"Error clearing history: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'timestamp': datetime.datetime.now().isoformat()})

if __name__ == '__main__':
    # Don't use debug=True in production
    port = int(os.environ('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
