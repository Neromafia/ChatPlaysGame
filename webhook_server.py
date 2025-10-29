# webhook_server.py
# Server trung gian chạy 24/7 trên Host Free (Glitch/Fly.io)

from flask import Flask, request, jsonify
import db_manager  # Import logic database
import config      # Import cấu hình
import math

app = Flask(__name__)

# --- HÀM XỬ LÝ KINH TẾ (Lấy từ command_handler) ---
# Chúng ta sao chép logic nạp tiền sang đây

def process_recharge(user_id, username, amount_str, source, message=""):
    """
    Xử lý nạp tiền (PayPal/MoMo) và cộng Keys/EXP/Points.
    """
    try:
        if source == "PP": # PayPal (amount_str là USD)
            amount_usd = float(amount_str)
            amount_vnd = amount_usd * config.USD_TO_VND_RATE
        elif source == "MM": # MoMo (amount_str là VND)
            amount_vnd = int(amount_str)
            amount_usd = amount_vnd / config.USD_TO_VND_RATE
    except Exception as e:
        print(f"LỖI (Webhook): Định dạng tiền tệ không hợp lệ {amount_str}. Lỗi: {e}")
        return False, "Lỗi định dạng tiền"

    keys_added = 0
    points_added = 0
    exp_added = 0

    if source == "MM" and "exp" in message.lower(): 
        exp_added = math.floor(amount_vnd * config.EXP_PER_VND_DIRECT)
    else:
        if source == "MM":
            points_added = math.floor(amount_usd * config.POINTS_PER_USD_DIRECT)
            exp_added = math.floor(amount_vnd * config.EXP_PER_VND_DIRECT) 
        else: # PP
            keys_added = math.floor(amount_usd * config.KEYS_PER_USD_DIRECT)
            exp_added = math.floor(keys_added * config.BASE_EXP_PER_KEY_PURCHASED) 
    
    data = db_manager.get_viewer_data(user_id, username)
    if not data: 
        data = db_manager.create_new_viewer(db_manager.get_worksheet(), user_id, username)
        if not data:
             print(f"LỖI (Webhook): Không thể tạo user mới {username}")
             return False, "Lỗi tạo user"

    db_manager.update_user_stats(
        user_data=data,
        add_points=points_added,
        add_exp=exp_added,
        add_keys=keys_added
    )
    
    result_str = f"NẠP THÀNH CÔNG: {username} +{keys_added} Keys, +{exp_added} EXP, +{points_added} P."
    print(result_str)
    return True, result_str

# --- ENDPOINT (ĐIỂM NHẬN WEBHOOK) ---
# Đây là URL mà Ngân Lượng sẽ gọi: https://ten-mien-cua-ban.glitch.me/webhook
@app.route('/webhook', methods=['POST'])
def handle_webhook():
    """Lắng nghe tín hiệu POST từ Ngân Lượng."""
    try:
        data = request.json # Nhận dữ liệu JSON từ Ngân Lượng
        
        # --- BẠN PHẢI TỰ ĐIỀU CHỈNH CÁC BIẾN NÀY ---
        # (Dựa trên tài liệu API của Ngân Lượng)
        # Giả sử Ngân Lượng gửi về:
        # data = {
        #    "transaction_id": "NL_123",
        #    "amount_vnd": 50000,
        #    "message": "exp UCa-xyz",
        #    "secret_key": "KEY_BI_MAT_CUA_BAN"
        # }
        
        # 1. Xác thực (Đơn giản)
        # (Nên đặt một mã bí mật trong Ngân Lượng để xác minh)
        # if data.get('secret_key') != "KEY_BI_MAT_CUA_BAN":
        #    return jsonify({"status": "error", "message": "Sai khóa bảo mật"}), 401
            
        # 2. Phân tích dữ liệu
        amount_vnd = data.get('amount_vnd')
        message = data.get('message', "")
        
        # Tách ID YouTube từ lời nhắn
        # (Giả sử ID luôn ở cuối lời nhắn)
        parts = message.split()
        if not parts:
            raise Exception("Lời nhắn rỗng, không có ID YouTube")
            
        user_id = parts[-1] # Lấy phần tử cuối cùng làm ID
        
        # 3. Xử lý logic
        # (Hàm process_recharge đã bao gồm logic "exp" trong message)
        success, result_msg = process_recharge(user_id, f"MoMoUser_{user_id[:4]}", amount_vnd, "MM", message)
        
        if success:
            return jsonify({"status": "success", "message": result_msg}), 200
        else:
            return jsonify({"status": "error", "message": result_msg}), 400

    except Exception as e:
        print(f"LỖI WEBHOOK: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    # Chạy server (Glitch/Heroku sẽ tự động làm việc này)
    app.run(host='0.0.0.0', port=8080)