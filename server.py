import os
from flask import Flask, request, jsonify
from controller import manager

# Renderの環境変数からトークンを取得する
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")

# 【セキュリティチェック】もしトークンが設定されていなければエラー警告を出す
if not ACCESS_TOKEN:
    print("⚠️ 警告: 環境変数 'ACCESS_TOKEN' が設定されていません！")

app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({"status": "ok", "message": "Poker Server is Running!"})

@app.route("/join", methods=["POST"])
def join_game():
    data = request.json or {}
    name = data.get("name", "Player")
    
    # ★ クライアントから送られてきた「目標人数」を受け取る（送られてこなければデフォルト2人）
    target_players = data.get("target_players", 2)
    
    # ★ controllerのassign_roomに人数を渡す
    room_id, player_id = manager.assign_room(name, target_players=target_players)
    return jsonify({"room_id": room_id, "player_id": player_id})

@app.route("/leave", methods=["POST"])
def leave_game():
    data = request.json or {}
    room_id = int(data.get("room_id", 0))
    player_id = int(data.get("player_id", 0))
    
    # controllerのmanagerに退室処理を行わせる
    success = manager.leave_room(room_id, player_id)
    return jsonify({"success": success})

@app.route("/state", methods=["GET"])
def get_state():
    room_id = int(request.args.get("room_id", 0))
    player_id = int(request.args.get("player_id", 0))
    room = manager.rooms.get(room_id)
    if not room: return jsonify({"error": "Room not found"}), 404
    return jsonify(room.get_state(player_id))

@app.route("/action", methods=["POST"])
def player_action():
    data = request.json or {}
    room_id = int(data.get("room_id", 0))
    player_id = int(data.get("player_id", 0))
    act_type = data.get("act_type")
    amount = int(data.get("amount", 0))
    
    room = manager.rooms.get(room_id)
    if not room: return jsonify({"error": "Room not found"}), 404
    
    success = room.handle_action(player_id, act_type, amount)
    return jsonify({"success": success})

@app.route("/intermission", methods=["POST"])
def intermission_action():
    data = request.json or {}
    room_id = int(data.get("room_id", 0))
    room = manager.rooms.get(room_id)
    if not room: return jsonify({"error": "Room not found"}), 404
    
    if room.show_intermission:
        room.start_new_game()
    return jsonify({"success": True})

@app.route("/chat", methods=["POST"])
def send_chat():
    data = request.json or {}
    room_id = int(data.get("room_id", 0))
    player_name = data.get("name", "Unknown")
    msg = data.get("message", "")
    room = manager.rooms.get(room_id)
    if not room: return jsonify({"error": "Room not found"}), 404
    if msg:
        room.chat_logs.append(f"【{player_name}】: {msg}")
    return jsonify({"success": True})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)