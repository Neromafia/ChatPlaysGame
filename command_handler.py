# command_handler.py
import sys
import json
import random
import math
import db_manager # Import file database
import config # Import file cấu hình

# --- HÀM XỬ LÝ LỆNH CHÍNH TỪ STREAMER.BOT ---

def get_balance(user_id, username):
    """Lấy số dư (cho lệnh !points)."""
    try:
        data = db_manager.get_viewer_data(user_id, username)
        if data:
            safe_data = {
                "points": data.get('points', 0),
                "level": data.get('level', 1),
                "exp": data.get('exp', 0),
                "keys": data.get('keys', 0)
            }
            print(json.dumps(safe_data)) # In JSON để Streamer.bot đọc
        else:
            print(json.dumps({"error": "Lỗi khi lấy dữ liệu. Đang tạo user..."}))
    except Exception as e:
        print(json.dumps({"error": f"Lỗi Python: {e}"}))

def process_prediction(user_id, username, predict_team_raw, predict_amount_str):
    """Xử lý logic dự đoán '!b red 50'."""
    try:
        predict_amount = int(predict_amount_str)
    except:
        print("LỖI: Số Điểm dự đoán không hợp lệ. (Invalid Points amount)")
        return

    # --- LOGIC SONG NGỮ (MỚI) ---
    predict_team_normalized = predict_team_raw.upper()
    predict_team = "" 
    if predict_team_normalized in ["RED", "ĐỎ", "DO"]:
        predict_team = "RED"
    elif predict_team_normalized in ["BLUE", "XANH", "XANH DUONG"]:
        predict_team = "BLUE"
    else:
        print("LỖI: Màu dự đoán không hợp lệ. (Invalid color. Use RED or BLUE).")
        return
    # --- KẾT THÚC LOGIC SONG NGỮ ---

    data = db_manager.get_viewer_data(user_id, username)
    if not data:
        print("LỖI: Không tìm thấy user.")
        return

    # 1. Kiểm tra Giới hạn
    max_prediction = int(data['points'] * config.MAX_PREDICTION_PERCENTAGE)
    if predict_amount < config.MIN_PREDICTION:
        print(f"LỖI: Dự đoán tối thiểu là {config.MIN_PREDICTION} P.")
        return
    if predict_amount > max_prediction:
        print(f"LỖI: Dự đoán tối đa là {max_prediction} P (20% vốn).")
        return
    if data['points'] < predict_amount:
        print("LỖI: Không đủ Điểm (P) để dự đoán.")
        return

    # 2. Trừ Điểm (P) và Cộng EXP (Cày cuốc)
    exp_gained = predict_amount * config.EXP_PER_POINT_COMMITTED
    success = db_manager.update_user_stats(
        user_data=data,
        add_points= -predict_amount, # Trừ Điểm
        add_exp=exp_gained
    )
    
    if success:
        # 3. Ghi dự đoán vào file tạm thời
        prediction_entry = {"id": user_id, "username": username, "team": predict_team, "amount": predict_amount}
        with open("current_predictions.json", "a", encoding="utf-8") as f: 
            f.write(json.dumps(prediction_entry) + '\n')
            
        # 4. Cộng vào Quỹ Chung
        pool_contribution = math.floor(predict_amount * config.POOL_CONTRIBUTION_RATE)
        db_manager.update_jackpot_pool(pool_contribution)
        
        # 5. Cập nhật Pool tính Odds
        db_manager.update_prediction_pool(predict_team, predict_amount)
            
        print(f"THÀNH CÔNG: {username} dự đoán {predict_amount} P cho {predict_team}.")
    else:
        print("LỖI: Không thể cập nhật Database.")

def process_recharge(user_id, username, amount_str, source, message=""):
    """Xử lý nạp tiền (SC/PayPal/MoMo) và cộng Keys/EXP/Points."""
    
    try:
        if source == "SC": # SuperChat (amount_str là "Micros")
             amount_usd = int(amount_str) / 1000000 
        elif source == "PP": # PayPal (amount_str là USD)
            amount_usd = float(amount_str)
        elif source == "MM": # MoMo (amount_str là VND)
            amount_vnd = int(amount_str)
            amount_usd = amount_vnd / config.USD_TO_VND_RATE
    except Exception as e:
        print(f"LỖI: Định dạng tiền tệ không hợp lệ {amount_str}. Lỗi: {e}")
        return

    keys_added = 0
    points_added = 0
    exp_added = 0

    if source == "MM" and "exp" in message.lower(): 
        exp_added = math.floor(amount_vnd * config.EXP_PER_VND_DIRECT)
    else:
        if source == "MM":
            points_added = math.floor(amount_usd * config.POINTS_PER_USD_DIRECT)
            exp_added = math.floor(amount_vnd * config.EXP_PER_VND_DIRECT) 
        else: # SC/PP
            keys_added = math.floor(amount_usd * (config.KEYS_PER_USD_SC if source == "SC" else config.KEYS_PER_USD_DIRECT))
            exp_added = math.floor(keys_added * config.BASE_EXP_PER_KEY_PURCHASED) 
    
    data = db_manager.get_viewer_data(user_id, username)
    if not data: return

    db_manager.update_user_stats(
        user_data=data,
        add_points=points_added,
        add_exp=exp_added,
        add_keys=keys_added
    )
    print(f"NẠP THÀNH CÔNG: {username} +{keys_added} Keys, +{exp_added} EXP, +{points_added} P.")

def process_gacha(user_id, username, amount_str="1"):
    """Xử lý mở Gacha (!open)."""
    try:
        keys_to_open = int(amount_str)
    except: keys_to_open = 1
        
    data = db_manager.get_viewer_data(user_id, username)
    if not data or data['keys'] < keys_to_open:
        print("LỖI: Bạn không đủ Key để mở.")
        return

    # Trừ Keys
    db_manager.update_user_stats(data, add_keys= -keys_to_open)
    
    results_summary = {}
    total_exp_gained = 0
    total_points_gained = 0
    inventory_updates = data.get('inventory', {})

    for _ in range(keys_to_open):
        roll = random.random()
        cumulative_prob = 0
        for item_key, probability in config.LOOT_TABLE.items():
            cumulative_prob += probability
            if roll <= cumulative_prob:
                if item_key == 'VIP_5_LIFETIME':
                    inventory_updates['VIP_5_LIFETIME'] = True
                    results_summary[item_key] = results_summary.get(item_key, 0) + 1
                elif item_key == 'X2_PAYOUT_TICKET':
                    inventory_updates['X2_PAYOUT_TICKET'] = inventory_updates.get('X2_PAYOUT_TICKET', 0) + 1
                    results_summary[item_key] = results_summary.get(item_key, 0) + 1
                elif item_key == 'INSURANCE_TICKET':
                    inventory_updates['INSURANCE_TICKET'] = inventory_updates.get('INSURANCE_TICKET', 0) + 1
                    results_summary[item_key] = results_summary.get(item_key, 0) + 1
                elif item_key.startswith('EXP'):
                    if item_key == 'EXP_LARGE': exp_val = 500
                    elif item_key == 'EXP_MEDIUM': exp_val = 150
                    else: exp_val = 50 
                    total_exp_gained += exp_val
                elif item_key.startswith('POINTS'):
                    if item_key == 'POINTS_JACKPOT': chip_val = 5000
                    else: chip_val = 100
                    total_points_gained += chip_val
                break 
                
    db_manager.update_user_stats(data, 
                                 add_points=total_points_gained, 
                                 add_exp=total_exp_gained,
                                 new_inventory=inventory_updates)

    final_result_str = f"Mở {keys_to_open} hộp: Trúng {total_points_gained} P, {total_exp_gained} EXP"
    item_list = [f"{v}x {k.replace('_', ' ')}" for k, v in results_summary.items()]
    if item_list:
        final_result_str += ", và: " + ", ".join(item_list)
        
    print(final_result_str) # In kết quả để Streamer.bot đọc

def set_member_tier(user_id, username, tier_name):
    """Cập nhật cấp bậc Hội viên trong DB."""
    data = db_manager.get_viewer_data(user_id, username)
    if not data: return
    
    db_manager.update_user_stats(user_data=data, new_member_tier=tier_name)
    print(f"CẬP NHẬT: {username} giờ là Hội viên Cấp {tier_name}.")

# --- BỘ ĐIỀU PHỐI (ROUTER) ---
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("LỖI: Thiếu tham số (command, userId).")
        sys.exit()

    command = sys.argv[1]
    user_id = sys.argv[2]
    
    try:
        if command == "get_balance":
            username = sys.argv[3]
            get_balance(user_id, username)
            
        elif command == "process_prediction":
            username = sys.argv[3]
            predict_team_raw = sys.argv[4] 
            predict_amount = sys.argv[5]
            process_prediction(user_id, username, predict_team_raw, predict_amount)

        elif command == "process_sc":
            username = sys.argv[3]
            amount_micros = sys.argv[4]
            process_recharge(user_id, username, amount_micros, "SC")
            
        elif command == "process_momo_file":
            raw_data = sys.argv[2] # %file_data% (UCa-xyz,50000,exp)
            parts = raw_data.strip().split(',')
            if len(parts) >= 2:
                user_id_from_file = parts[0]
                amount_vnd = parts[1]
                message = parts[2] if len(parts) > 2 else ""
                process_recharge(user_id_from_file, f"MoMoUser_{user_id_from_file[:4]}", amount_vnd, "MM", message)
            else:
                print("LỖI: File MoMo không đúng định dạng (cần ID,Amount).")

        elif command == "process_paypal_file":
            raw_data = sys.argv[2] # (UCa-xyz,10)
            parts = raw_data.strip().split(',')
            if len(parts) >= 2:
                user_id_from_file = parts[0]
                amount_usd = parts[1]
                process_recharge(user_id_from_file, f"PayPalUser_{user_id_from_file[:4]}", amount_usd, "PP")
            else:
                print("LỖI: File PayPal không đúng định dạng (cần ID,Amount).")
                
        elif command == "process_exp_file":
            raw_data = sys.argv[2] # (UCa-xyz,50000)
            parts = raw_data.strip().split(',')
            if len(parts) >= 2:
                user_id_from_file = parts[0]
                amount_vnd = parts[1]
                process_momo_exp_only(user_id_from_file, f"MoMoUser_{user_id_from_file[:4]}", amount_vnd, "MM")
            else:
                print("LỖI: File EXP không đúng định dạng (cần ID,Amount).")

        elif command == "open_gacha":
            username = sys.argv[3]
            amount = sys.argv[4] if len(sys.argv) > 4 else "1"
            process_gacha(user_id, username, amount)
            
        elif command == "set_member_tier":
            username = sys.argv[3]
            tier_name = sys.argv[4]
            set_member_tier(user_id, username, tier_name)

    except Exception as e:
        print(f"LỖI THỰC THI PYTHON (command_handler.py): {e}")