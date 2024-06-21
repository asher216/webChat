from flask import Blueprint, Flask, flash, jsonify, redirect, render_template, request, url_for
from flask_login import login_required, current_user
from .models import Contact, User, Message
from .auth import Authenticate
from . import db
# import json
import os
from cryptography.fernet import Fernet
from werkzeug.utils import secure_filename
# import requests
# import time
from uuid import uuid4
import pathlib   
import google.generativeai as genai
import copy
import io
from PIL import Image
from werkzeug.datastructures import FileStorage
import ffmpeg
import tempfile


views = Blueprint('views', __name__)
genai.configure(api_key="AIzaSyDyYOc-09ZQmz55tvXB-ykTTnmlxjReC6I")

class Encryption:
    def __init__(self):
        self.key = self.load_key_from_env()
        
    def load_key_from_env(self):
        key = os.environ.get("SECRET_KEY")
        if key is None:
            raise ValueError("Secret key not found in environment variables.")
        return key.encode()

    def encrypt_message(self, message):
        fernet = Fernet(self.key)
        encrypted_message = fernet.encrypt(message.encode()).decode()
        return encrypted_message

    def decrypt_message(self, encrypted_message):
        fernet = Fernet(self.key)
        decrypted_message = fernet.decrypt(encrypted_message.encode()).decode()
        return decrypted_message


class FileHandling:
    def get_file_type(file):
        kind = pathlib.Path(file.filename).suffix
        return kind
    
    def compress_image(file, quality=20):
        img = Image.open(file)
        
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            # Discard the alpha channel
            background = Image.new("RGB", img.size, (255, 255, 255))
            background.paste(img, mask=img.split()[3] if img.mode == "RGBA" else None)
            img = background
        else:
            img = img.convert("RGB")
        
        img_io = io.BytesIO()  # Create a BytesIO object to save the compressed image
        img.save(img_io, format='JPEG', quality=quality)  

        img_io.seek(0)  # Rewind the file-like object to the start
        compressed_file = FileStorage(stream=img_io, filename=file.filename.replace(".png", ".jpg"), content_type="image/jpeg")
        return compressed_file
        
    
    def process_file(file):
        file_type = FileHandling.get_file_type(file)
        if file_type.lower() == '.jpg' or file_type.lower() == '.jpeg' or file_type.lower() == '.png':
            file = FileHandling.compress_image(file)
            
        filename = secure_filename(file.filename)
        random_str = uuid4().hex[:8]
        unique_filename = f"{random_str}_{filename}"
        
        file.filename = unique_filename
        return file
    

   
@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    return render_template("add_new.html", user=current_user)

@views.route('/add-contact', methods=['GET', 'POST'])
@login_required
def add_contact():
    if request.method == 'POST':
        email = request.form.get('email')
        name = request.form.get('name')
        user = User.query.filter_by(email=email).first()
        if user:
            user_added=False
            for contact in current_user.contacts:
                if email == contact.contact_email:
                    flash("User already added!", category="error")
                    user_added = True
                    break 
            if user_added == False:
                if email == current_user.email:
                    flash("Cannot add yourself!", category='error')
                else:
                    new_contact = Contact(name=name, current_user_id=current_user.id, contact_id=user.id, contact_email=email)
                    db.session.add(new_contact)
                    new_contact = Contact(name=current_user.first_name, current_user_id=user.id, contact_id=current_user.id, contact_email=current_user.email)
                    db.session.add(new_contact)
                    db.session.commit()
                    flash('User added to contacts!', category="success")
                    return redirect(url_for('views.send_msg', id_num=user.id))
        else: 
            flash('User not found!', category="error")

        
    return render_template("add_new.html", user=current_user)


@views.route('/send-msg/<int:id_num>', methods=['GET', 'POST'])
@login_required
def send_msg(id_num):
    encryptor = Encryption()
    if request.method == 'POST':
        message = request.form.get('message')
        file = request.files.get('upload-file')

        if file:
            
            file = FileHandling.process_file(file)
            if message:     
                encrypted_message = encryptor.encrypt_message(message)
            else:
                encrypted_message = ""  

            file.save(os.path.join('C:/cyber/cyberProject/myWebsite/website/static/uploads', file.filename))
            new_message = Message(data=encrypted_message, filename=os.path.join('static/uploads', file.filename), sender_id=current_user.id, receiver_id=id_num)
            db.session.add(new_message)
            db.session.commit()
            flash('Message sent!', category='success')
            return jsonify({'status': 'success'}), 200
        else:
            if message != '' and not message.startswith("\r\n"):
                encrypted_message = encryptor.encrypt_message(message)  
                new_message = Message(data=encrypted_message, sender_id=current_user.id, receiver_id=id_num)
                db.session.add(new_message)
                db.session.commit()
                flash('Message sent!', category='success')
                return jsonify({'status': 'success'}), 200
            else:
                flash("please enter text!!", category="error")
                return jsonify({'status': 'failure'}), 400
    user_messages=retrieve_messages(current_user.id, id_num, encryptor)
    to_contact=Contact.query.filter_by(contact_id=id_num).filter_by(current_user_id=current_user.id).first()
    return render_template("message_sender.html", user=current_user, to_contact=Contact.query.filter_by(contact_id=id_num).filter_by(current_user_id=current_user.id).first(), user_messages=user_messages)







@views.route('/get-new-messages/<int:receiver_id>', methods=['GET'])
@login_required
def get_new_messages(receiver_id):
    encryptor = Encryption()
    new_messages = retrieve_new_messages(current_user.id, receiver_id, encryptor)
    # Convert Message objects to dictionaries
    message_data = []
    for message in new_messages:
        message_data.append({
            'id': message.id,  # Assuming Message has an ID field
            'data': message.data,  # Assuming Message has a data field (encrypted message)
            'filename': message.filename,
            'sender_id': message.sender_id,  # Assuming Message has a sender_id field
            'date': message.date,
            'receiver_id': message.receiver_id
        })
    return jsonify(messages= message_data)











@views.route('/ai-process', methods=['POST'])
@login_required
def process_text():
    # Get the text from the form submission
    text = request.json.get('message')
    
    # Process the text using the AI model
    ai_response = generate_ai_response(text)

    return jsonify({'ai_response': ai_response})
    

    
def retrieve_messages(sender_id, receiver_id, encryptor):
    user_messages = Message.query.filter((Message.sender_id == sender_id) & (Message.receiver_id == receiver_id) | (Message.sender_id == receiver_id) & (Message.receiver_id == sender_id)).all()
    decrypted_messages = []
    for message in user_messages:
        temp_msg = copy.copy(message)
        if temp_msg.data:
            decrypted_message= encryptor.decrypt_message(temp_msg.data)
            temp_msg.data=decrypted_message
            decrypted_messages.append(temp_msg)
        elif temp_msg.filename:
            decrypted_messages.append(temp_msg)
    if decrypted_messages:
        current_user.last_message_id = decrypted_messages[-1].id
        db.session.commit()
    return decrypted_messages

def retrieve_new_messages(sender_id, receiver_id, encryptor):
    last_seen_message_id = current_user.last_message_id
    user_messages = Message.query.filter(((Message.sender_id == sender_id) & (Message.receiver_id == receiver_id) | (Message.sender_id == receiver_id) & (Message.receiver_id == sender_id)) & (Message.id > last_seen_message_id)).all()
    decrypted_messages = []
    for message in user_messages:
        temp_msg = copy.copy(message)
        if temp_msg.data:
            decrypted_message= encryptor.decrypt_message(temp_msg.data)
            temp_msg.data=decrypted_message
            decrypted_messages.append(temp_msg)
        elif temp_msg.filename:
            decrypted_messages.append(temp_msg)
    if decrypted_messages:
        current_user.last_message_id = decrypted_messages[-1].id
        db.session.commit()
    return decrypted_messages


def generate_ai_response(message):

    generation_config = {
    "temperature": 1,
    "top_p": 0.95,
    "top_k": 0,
    "max_output_tokens": 8192,
    }

    safety_settings = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_MEDIUM_AND_ABOVE"
    },
    ]

    model = genai.GenerativeModel(model_name="gemini-1.5-pro-latest",
                                generation_config=generation_config,
                                safety_settings=safety_settings)

    convo = model.start_chat(history=[
    {
        "role": "user",
        "parts": ["all my next messages are for a chat application where a user sends something to you and you answer and your answer will show in a chat textbox available for sending"]
    },
    {
        "role": "model",
        "parts": ["Got it! I'm ready to respond to your chat messages as if I were in a chat application. Just send me the user's message, and I'll provide a suitable reply for the chat textbox. 💬"]
    },
    ])

    convo.send_message(message)
    return convo.last.text

