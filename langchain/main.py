import os
import uuid
import asyncio
import requests
import base64
from datetime import datetime
from flask import jsonify
import functions_framework
from google.cloud import firestore
from langchain.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.schema import Document, SystemMessage, HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from google import genai
from google.genai import types

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
db = firestore.Client()

nyssa_llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash-lite",  
    google_api_key=GOOGLE_API_KEY,
    convert_system_message_to_human=True,
    temperature=0.7
)

SUMMARY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "Summarize the following conversation history into a concise paragraph:"),
    ("user", "{context}")
])
SUMMARY_CHAIN = create_stuff_documents_chain(llm=nyssa_llm, prompt=SUMMARY_PROMPT)

def summarize_messages(messages):
    formatted = "\n".join(f"{msg['role']}: {msg['content']}" for msg in messages)
    doc = Document(page_content=formatted)
    return SUMMARY_CHAIN.invoke({"context": [doc]})

def create_thread(user_id):
    try:
        now_iso = datetime.utcnow().isoformat()
        thread_id = str(uuid.uuid4()).upper()
        thread_data = {
            'userId': user_id,
            'messages': [],
            'created_at': now_iso,
            'modified_at': now_iso,
            'status': 'active'
        }
        db.collection('nyssaChatThreads').document(thread_id).set(thread_data)
        thread_data['id'] = thread_id
        return thread_data
    except Exception as e:
        print(f"Error creating thread: {e}")
        return None

def get_thread(thread_id):
    try:
        doc_ref = db.collection('nyssaChatThreads').document(thread_id)
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            data['id'] = thread_id
            return data
        return None
    except Exception as e:
        print(f"Error getting thread: {e}")
        return None

def update_thread_messages(thread_id, messages):
    try:
        now_iso = datetime.utcnow().isoformat()
        db.collection('nyssaChatThreads').document(thread_id).update({
            'messages': messages,
            'modified_at': now_iso
        })
        return True
    except Exception as e:
        print(f"Error updating thread: {e}")
        return False

@functions_framework.http
def nyssaLangchain(request):
    try:
        try:
            asyncio.get_event_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())
        
        req_json = request.get_json(silent=True)
        if not req_json or 'input' not in req_json:
            return jsonify({"error": "Missing 'input' in request body"}), 400
        
        user_input = req_json['input']
        thread_id = req_json.get('threadId')
        user_id = req_json.get('userId')
        
        if thread_id:
            thread = get_thread(thread_id)
            if not thread:
                thread = create_thread(user_id)
        else:
            thread = create_thread(user_id)
            if not thread:
                return jsonify({"error": "Failed to create thread"}), 500
        
        messages = thread.get('messages', [])
        if len(messages) > 14:
            summary = summarize_messages(messages[:-14])
            messages = [{'role': 'system', 'content': summary}] + messages[-14:]
        
        image_inputs = req_json.get('images', [])
        single_image = req_json.get('image')
        if isinstance(single_image, list):
            image_inputs.extend(single_image)
        elif single_image:
            image_inputs.append(single_image)

        try:
            messages_for_llm = []
            for msg in messages:
                if msg['role'] == 'user':
                    messages_for_llm.append(HumanMessage(content=msg['content']))
                elif msg['role'] == 'assistant':
                    messages_for_llm.append(AIMessage(content=msg['content']))
                elif msg['role'] == 'system':
                    messages_for_llm.append(SystemMessage(content=msg['content']))

            # Add system message
            messages_for_llm.append(SystemMessage(content="You are Nyssa, a helpful and knowledgeable AI assistant. When provided with images, analyze them in detail and describe what you see."))
            
            # Process images if present
            if image_inputs:
                # Prepare multimodal content
                multimodal_content = [{"type": "text", "text": user_input}]
                
                for i, image_url in enumerate(image_inputs[:2]):
                    try:
                        image_response = requests.get(image_url.strip())
                        if image_response.status_code != 200:
                            return jsonify({"error": f"Failed to download image {i+1} from URL"}), 400
                        
                        # Convert image to base64
                        image_b64 = base64.b64encode(image_response.content).decode('utf-8')
                        multimodal_content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}"
                            }
                        })
                    except requests.exceptions.RequestException as e:
                        return jsonify({"error": f"Failed to download image {i+1}: {str(e)}"}), 400
                
                # Create multimodal message
                user_message = HumanMessage(content=multimodal_content)
            else:
                user_message = HumanMessage(content=user_input)
            
            messages_for_llm.append(user_message)
            
            # Debug print
            print(f"Sending message with {len(image_inputs)} images")
            
            response = nyssa_llm.invoke(messages_for_llm)
            final_response = response.content
            
            messages.append({'role': 'user', 'content': user_input})
            messages.append({'role': 'assistant', 'content': final_response})
            update_thread_messages(thread['id'], messages)
            
            return jsonify({
                "threadId": thread['id'],
                "response": final_response,
                "success": True
            })
            
        except Exception as e:
            print(f"Error in conversation: {e}")
            return jsonify({"error": f"Conversation failed: {e}"}), 500
    
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:
        print(f"Exception occurred: {e}")
        return jsonify({"error": f"Internal server error: {e}"}), 500