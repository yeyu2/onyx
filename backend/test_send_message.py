import requests
import json
import uuid
import sys
from onyx.utils.logger import setup_logger

# Import our direct print utility
sys.path.insert(0, '.')
from debug_force_print import enable_direct_prints

# Enable direct prints
enable_direct_prints()

# Setup logger
logger = setup_logger(__name__)

def test_send_message():
    # Create a unique session ID
    session_id = str(uuid.uuid4())
    base_url = "http://localhost:8000"
    
    # Create chat session
    create_session_url = f"{base_url}/api/chat/create-chat-session"
    create_session_payload = {
        "description": "Test Chat Session",
        "persona_id": 1
    }
    
    try:
        session_response = requests.post(
            create_session_url, 
            json=create_session_payload,
            headers={"Content-Type": "application/json"}
        )
        
        if session_response.status_code != 200:
            print(f"Failed to create session: {session_response.status_code}")
            return
        
        session_data = session_response.json()
        chat_session_id = session_data.get('chat_session_id')
        
        # Send message to chat session
        send_message_url = f"{base_url}/api/chat/send-message"
        message_payload = {
            "message": "Hello, this is a test message",
            "chat_session_id": chat_session_id,
            "prompt_id": None,
            "document_choice": []
        }
        
        message_response = requests.post(
            send_message_url,
            json=message_payload,
            headers={"Content-Type": "application/json"},
            stream=True
        )
        
        if message_response.status_code != 200:
            print(f"Failed to send message: {message_response.status_code}")
            return
        
        # Process streaming response
        for line in message_response.iter_lines():
            if line:
                print(f"Response: {line.decode('utf-8')}")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_send_message() 