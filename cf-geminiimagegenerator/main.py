import os
import uuid
import base64
import asyncio
import requests
import functions_framework
from flask import jsonify
from google.cloud import storage
from google import genai
from google.genai import types

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

@functions_framework.http
def gemini_image_generator(request):
    try:
        try:
            asyncio.get_event_loop()
        except RuntimeError:
            asyncio.set_event_loop(asyncio.new_event_loop())
            
        req_json = request.get_json(silent=True)
        if not req_json or 'input' not in req_json:
            return jsonify({"error": "Missing 'input' in request body"}), 400
        
        text_input = req_json['input']
        
        image_inputs = req_json.get('images', [])
        single_image = req_json.get('image')
        if isinstance(single_image, list):
            image_inputs.extend(single_image)
        elif single_image:
            image_inputs.append(single_image)
            
        try:
            contents = [f"Text: {text_input}"]
            
            if image_inputs:
                for i, image_url in enumerate(image_inputs[:2]):
                    try:
                        image_response = requests.get(image_url.strip())
                        if image_response.status_code != 200:
                            return jsonify({"error": f"Failed to download image {i+1} from URL"}), 400
                        
                        contents.append(
                            types.Part.from_bytes(data=image_response.content, mime_type="image/jpeg")
                        )
                    except requests.exceptions.RequestException as e:
                        return jsonify({"error": f"Failed to download image {i+1}: {str(e)}"}), 400
            
            client = genai.Client(api_key=GOOGLE_API_KEY)
            response = client.models.generate_content(
                model="models/gemini-2.0-flash-exp",
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["Text", "Image"]
                )
            )
            
            final_text = ""
            final_image_base64 = ""
            if response.candidates and len(response.candidates) > 0:
                if response.candidates[0].content and hasattr(response.candidates[0].content, 'parts'):
                    for part in response.candidates[0].content.parts:
                        if part.text is not None:
                            final_text += part.text
                        elif part.inline_data is not None:
                            final_image_base64 = base64.b64encode(part.inline_data.data).decode("utf-8")
            
            image_link = ""
            if final_image_base64:
                storage_client = storage.Client()
                bucket = storage_client.bucket("linear-rig-452607-n8.firebasestorage.app")
                file_name = f"chatGenImages/{uuid.uuid4()}.png"
                image_bytes = base64.b64decode(final_image_base64)
                blob = bucket.blob(file_name)
                blob.upload_from_string(image_bytes, content_type="image/png")
                blob.make_public()
                image_link = blob.public_url
            
            return jsonify({
                "text": final_text,
                "image_url": image_link,
                "success": True
            })
            
        except Exception as e:
            print(f"Error in image processing: {e}")
            return jsonify({"error": f"Image processing failed: {e}"}), 500
    
    except Exception as e:
        print(f"Exception occurred: {e}")
        return jsonify({"error": f"Internal server error: {e}"}), 500