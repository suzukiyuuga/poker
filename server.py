import os
import requests as http_requests
from flask import Flask, request, jsonify
from controller import manager

ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

if not ACCESS_TOKEN:
    print("⚠️ 警告: 環境変数 'ACCESS_TOKEN' が設定されていません！")

app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({"status": "ok", "message": "Poker Server is Running!"})

@app.route("/join", methods=["POST"])
def join_game():#入室処理
    data = request.json or {}
    name = data.get("name", "Player")
    
    # ★ controllerの変更に基づき、部屋番号、プレイヤーID、およびホストかどうかのフラグを受け取る
    room_id, player_id, is_host = manager.assign_room(name)
    room = manager.rooms.get(room_id)
    
    return jsonify({
        "room_id": room_id, 
        "player_id": player_id, 
        "is_host": is_host,
        "target_players": room.target_players if room else 2
    })

@app.route("/setup_room", methods=["POST"])
def setup_room():
    # ★ ホストプレイヤーが人数を確定した際に叩かれる新しいAPIルート
    data = request.json or {}
    room_id = int(data.get("room_id", 0))
    target_players = int(data.get("target_players", 2))
    
    room = manager.rooms.get(room_id)
    if not room: 
        return jsonify({"error": "Room not found"}), 404
        
    # 部屋の目標プレイ人数をホストが指定した値に更新
    room.target_players = target_players
    
    # ログ内の最初の一人の参加メッセージ部分を正しい目標人数に書き直す調整
    if len(room.action_logs) > 0 and "が参加しました" in room.action_logs[0]:
        room.action_logs[0] = f"📢 {room.players[0].name} が参加しました。({len(room.players)}/{room.target_players})"
        
    # 人数がすでに満たされているかチェックし、満たされていればゲームを開始
    room.check_start_trigger()
    return jsonify({"success": True, "target_players": room.target_players})

@app.route("/leave", methods=["POST"])
def leave_game():#退出処理
    data = request.json or {}
    room_id = int(data.get("room_id", 0))
    player_id = int(data.get("player_id", 0))
    
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
def player_action():#プレイヤーの行動をサーバーに送信
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
    player_id = int(data.get("player_id", -1))
    player_name = data.get("name", "Unknown")
    msg = data.get("message", "")
    room = manager.rooms.get(room_id)
    if not room: return jsonify({"error": "Room not found"}), 404

    if msg:
        if msg.startswith("/advice"):
            if not OPENAI_API_KEY:
                advice_msg = "💡 【AI助言】サーバー側で OPENAI_API_KEY が設定されていないため、助言機能を利用できません。"
            else:
                prompt_text = room.get_advice_prompt(player_id, msg)
                try:
                    res = http_requests.post(
                        "https://api.openai.com/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {OPENAI_API_KEY}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "gpt-4o-mini",
                            "messages": [
                                {"role": "system", "content": "あなたはテキサスホールデム・ポーカーのアドバイザーです。プレイヤーの状況(自分の手札、場札、チップ量)のみを元に、短く的確にアドバイスしてください。"},
                                {"role": "user", "content": prompt_text}
                            ],
                            "max_tokens": 150
                        },
                        timeout=10
                    )
                    if res.status_code == 200:
                        advice = res.json()["choices"][0]["message"]["content"].strip()
                        advice_msg = f"💡 【AI助言】\n{advice}"
                    else:
                        advice_msg = f"💡 【AI助言エラー】APIからの応答に失敗しました。(Status: {res.status_code})"
                except Exception as e:
                    advice_msg = f"💡 【AI助言エラー】通信エラーが発生しました: {e}"

            room.send_private_message(player_id, advice_msg)
        else:
            room.chat_logs.append(f"【{player_name}】: {msg}")
            
    return jsonify({"success": True})

if __name__ == "__main__":#このファイルが直接動かされた時
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)