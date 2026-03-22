import os
from flask import Flask, send_from_directory, request, jsonify
from flask_socketio import SocketIO, emit
import json
import time
import uuid

app = Flask(__name__, static_folder='static')
app.config['SECRET_KEY'] = 'molv-secret-key-2024'
socketio = SocketIO(app, cors_allowed_origins="*")

# Хранилище данных
messages = []
users = {}
friends = {}
friend_requests = {}
online_users = set()

@app.route('/')
def index():
    print("=== Root route called ===")
    print("Current directory:", os.getcwd())
    print("Files in static:", os.listdir('static') if os.path.exists('static') else "static not found")
    return send_from_directory('static', 'index.html')

@app.route('/test')
def test():
    return "Сервер работает! ✅"

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    
    if username not in users:
        users[username] = {'created': time.time()}
        friends[username] = []
        friend_requests[username] = []
    
    online_users.add(username)
    return jsonify({'status': 'ok', 'username': username})

@app.route('/api/users')
def get_users():
    user_list = [{'name': u, 'online': u in online_users} for u in users.keys()]
    return jsonify(user_list)

@app.route('/api/friends/<username>')
def get_friends(username):
    user_friends = friends.get(username, [])
    result = [{'name': f, 'online': f in online_users, 'unread': 0} for f in user_friends]
    return jsonify(result)

@app.route('/api/friend_requests/<username>')
def get_friend_requests(username):
    return jsonify(friend_requests.get(username, []))

@app.route('/api/messages/<username>')
def get_messages(username):
    user_messages = [m for m in messages if m.get('to') == username or m.get('from') == username]
    return jsonify(user_messages)

@socketio.on('send_message')
def handle_send_message(data):
    message = {
        'id': str(uuid.uuid4())[:8],
        'from': data['from'],
        'to': data['to'],
        'text': data.get('text', ''),
        'time': time.strftime('%H:%M'),
        'timestamp': time.time(),
        'read': False
    }
    messages.append(message)
    emit('new_message', message, room=data['to'])
    emit('message_sent', message, room=data['from'])

@socketio.on('add_friend')
def handle_add_friend(data):
    from_user = data['from']
    to_user = data['to']
    
    if to_user not in users:
        emit('error', {'message': 'Пользователь не найден'})
        return
    
    if to_user not in friend_requests:
        friend_requests[to_user] = []
    if from_user not in friend_requests[to_user]:
        friend_requests[to_user].append(from_user)
    
    emit('friend_request', {'from': from_user}, room=to_user)

@socketio.on('accept_friend')
def handle_accept_friend(data):
    current_user = data['current']
    friend_user = data['friend']
    
    if current_user not in friends:
        friends[current_user] = []
    if friend_user not in friends[current_user]:
        friends[current_user].append(friend_user)
    
    if friend_user not in friends:
        friends[friend_user] = []
    if current_user not in friends[friend_user]:
        friends[friend_user].append(current_user)
    
    if current_user in friend_requests and friend_user in friend_requests[current_user]:
        friend_requests[current_user].remove(friend_user)
    
    emit('friend_added', {'friend': friend_user}, room=current_user)
    emit('friend_added', {'friend': current_user}, room=friend_user)

@socketio.on('register_online')
def handle_register_online(data):
    username = data.get('username')
    if username:
        online_users.add(username)

application = app

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
