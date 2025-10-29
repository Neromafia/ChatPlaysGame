# db_manager.py
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timezone
import json
import math
from config import (
    SERVICE_ACCOUNT_FILE, SPREADSHEET_NAME, WORKSHEET_NAME, DB_COLS, 
    LEVEL_BASE, LEVEL_MULTIPLIER, JACKPOT_CELL, TOTAL_POOL_CELL, POOL_A_CELL, POOL_B_CELL,
    POINTS_PER_5_MIN, EXP_PER_MINUTE, MEMBER_MULTIPLIERS
)

_worksheet = None

def get_worksheet():
    """Chỉ kết nối Google Sheet MỘT LẦN (Singleton Pattern)."""
    global _worksheet
    if _worksheet is None:
        try:
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            creds = ServiceAccountCredentials.from_json_keyfile_name(SERVICE_ACCOUNT_FILE, scope)
            client = gspread.authorize(creds)
            _worksheet = client.open(SPREADSHEET_NAME).worksheet(WORKSHEET_NAME)
            print("✅ Kết nối Database (Google Sheet) thành công.")
        except Exception as e:
            print(f"❌ LỖI DATABASE: Không thể kết nối Google Sheet. Lỗi: {e}")
            return None
    return _worksheet

def get_viewer_data(youtube_id, username=None):
    """Tìm dữ liệu của viewer qua YouTube ID (Cột A) và tự động cộng điểm cày chay."""
    sheet = get_worksheet()
    if not sheet: return None

    try:
        data = sheet.find(youtube_id, in_column=DB_COLS["ID"])
        row_values = sheet.row_values(data.row)
        
        # Cập nhật username nếu có thay đổi
        if username and row_values[DB_COLS["USERNAME"]-1] != username:
            sheet.update_cell(data.row, DB_COLS["USERNAME"], username)
            
        user_data = {
            'row': data.row,
            'id': row_values[DB_COLS["ID"]-1],
            'username': username if username else row_values[DB_COLS["USERNAME"]-1],
            'points': int(row_values[DB_COLS["POINTS"]-1]),
            'exp': int(row_values[DB_COLS["EXP"]-1]),
            'level': int(row_values[DB_COLS["LEVEL"]-1]),
            'keys': int(row_values[DB_COLS["KEYS"]-1]),
            'inventory': json.loads(row_values[DB_COLS["INVENTORY"]-1]),
            'last_seen': row_values[DB_COLS["LAST_SEEN"]-1],
            'member_tier': row_values[DB_COLS["MEMBER_TIER"]-1]
        }
        
        # --- LOGIC ACTIVE FARMING (CÀY CHAY CHỦ ĐỘNG) ---
        try:
            last_seen_time = datetime.strptime(user_data['last_seen'], "%Y-%m-%d %H:%M:%S")
            time_diff_minutes = (datetime.now() - last_seen_time).total_seconds() / 60
            
            # Nếu đã 5 phút trôi qua kể từ lần chat cuối
            if time_diff_minutes >= 5:
                cycles = math.floor(time_diff_minutes / 5)
                
                # Lấy hệ số nhân của Member (nếu có)
                member_mult = MEMBER_MULTIPLIERS.get(user_data['member_tier'], 1.0)
                
                # Tính điểm P thưởng (dựa trên Level VÀ Member)
                level_bonus_mult = 1.0 + (user_data['level'] * config.LEVEL_BONUS_MULTIPLIER_PER_LEVEL)
                points_gained = math.floor(cycles * POINTS_PER_5_MIN * level_bonus_mult * member_mult)
                
                # Tính EXP thưởng (dựa trên thời gian VÀ Member)
                exp_gained = math.floor(cycles * 5 * EXP_PER_MINUTE * member_mult)
                
                if points_gained > 0 or exp_gained > 0:
                    update_user_stats(user_data, add_points=points_gained, add_exp=exp_gained, update_last_seen=True)
                    # Tải lại dữ liệu sau khi cập nhật
                    return get_viewer_data(youtube_id, username) 
                    
        except ValueError: # Xử lý lần đầu (Last_Seen rỗng)
             update_user_stats(user_data, update_last_seen=True) # Chỉ cập nhật thời gian
        
        return user_data

    except gspread.exceptions.CellNotFound:
        return create_new_viewer(sheet, youtube_id, username)
    except Exception as e:
        print(f"Lỗi khi đọc dữ liệu viewer {youtube_id}: {e}")
        return None

def create_new_viewer(sheet, youtube_id, username=None):
    """Tạo hồ sơ cơ bản cho Viewer mới."""
    print(f"Tạo user mới: {youtube_id}")
    new_username = username if username else f"User_{youtube_id[:6]}"
    
    new_row = [
        youtube_id,     # ID
        new_username,   # Username
        200,            # Points (P) khởi điểm
        0,              # EXP khởi điểm
        1,              # Level khởi điểm
        2,              # Keys khởi điểm
        json.dumps({}), # Inventory rỗng
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"), # Date_Joined
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"), # Last_Seen
        "default"       # Member_Tier
    ]
    sheet.append_row(new_row, value_input_option='USER_ENTERED')
    return get_viewer_data(youtube_id, username)

# --- HÀM CẬP NHẬT DỮ LIỆU (CORE) ---
def update_user_stats(user_data, add_points=0, add_exp=0, add_keys=0, new_inventory=None, update_last_seen=False, new_member_tier=None):
    """Cập nhật các chỉ số chính của user vào Google Sheet."""
    sheet = get_worksheet()
    if not sheet: return False

    try:
        batch_updates = []
        
        new_points = user_data['points'] + add_points
        new_exp = user_data['exp'] + add_exp
        new_keys = user_data['keys'] + add_keys
        
        batch_updates.append(gspread.Cell(user_data['row'], DB_COLS["POINTS"], new_points))
        batch_updates.append(gspread.Cell(user_data['row'], DB_COLS["EXP"], new_exp))
        
        new_level = calculate_level_from_exp(new_exp)
        if new_level != user_data['level']:
            batch_updates.append(gspread.Cell(user_data['row'], DB_COLS["LEVEL"], new_level))
            
        batch_updates.append(gspread.Cell(user_data['row'], DB_COLS["KEYS"], new_keys))
        
        if new_inventory is not None:
            batch_updates.append(gspread.Cell(user_data['row'], DB_COLS["INVENTORY"], json.dumps(new_inventory)))
            
        if new_member_tier is not None:
            batch_updates.append(gspread.Cell(user_data['row'], DB_COLS["MEMBER_TIER"], new_member_tier))

        if update_last_seen or add_points != 0 or add_exp != 0 or add_keys != 0:
            batch_updates.append(gspread.Cell(user_data['row'], DB_COLS["LAST_SEEN"], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

        sheet.update_cells(batch_updates, value_input_option='USER_ENTERED')
        
        print(f"DB Update: {user_data['username']} | Points: {add_points} | EXP: {add_exp} | Keys: {add_keys}")
        return True
    except Exception as e:
        print(f"Lỗi khi update_user_stats cho {user_data['username']}: {e}")
        return False

# --- HÀM TÍNH TOÁN ---
def calculate_level_from_exp(total_exp):
    """Tính Level hiện tại từ Tổng EXP (dựa trên Base 100, Multi 1.0239)."""
    if total_exp < LEVEL_BASE: return 1
    try:
        ratio = LEVEL_MULTIPLIER - 1
        n = math.log((total_exp * ratio / LEVEL_BASE) + 1) / math.log(LEVEL_MULTIPLIER)
        level = math.floor(n) + 1
        if level > 300: level = 300
        return level
    except Exception: return 1

# --- HÀM QUẢN LÝ QUỸ CHUNG (JACKPOT) ---
def get_jackpot_pool():
    sheet = get_worksheet()
    if not sheet: return 0
    try:
        return int(sheet.acell(JACKPOT_CELL).value)
    except: return 0

def update_jackpot_pool(amount_to_add, reset=False):
    sheet = get_worksheet()
    if not sheet: return
    
    current_pool = get_jackpot_pool()
    new_pool = 0 if reset else (current_pool + amount_to_add)
    
    sheet.update_acell(JACKPOT_CELL, new_pool)
    print(f"💰 Quỹ Thưởng Chung được cập nhật: {new_pool} P")

def reset_prediction_pools():
    """Reset các ô lưu trữ tổng cược (B1, C1, D1)."""
    sheet = get_worksheet()
    if not sheet: return
    try:
        sheet.update_acell(TOTAL_POOL_CELL, 0)
        sheet.update_acell(POOL_A_CELL, 0)
        sheet.update_acell(POOL_B_CELL, 0)
    except Exception as e:
        print(f"Lỗi reset pools: {e}")

def update_prediction_pool(team, amount):
    """Cộng dồn chip vào ô tổng cược (để tính Odds)."""
    sheet = get_worksheet()
    if not sheet: return
    try:
        # Cập nhật tổng pool
        current_total = int(sheet.acell(TOTAL_POOL_CELL).value)
        sheet.update_acell(TOTAL_POOL_CELL, current_total + amount)
        
        # Cập nhật pool của team
        cell_to_update = POOL_A_CELL if team == "RED" else POOL_B_CELL
        current_team_pool = int(sheet.acell(cell_to_update).value)
        sheet.update_acell(cell_to_update, current_team_pool + amount)
    except Exception as e:
        print(f"Lỗi update prediction pool: {e}")

def get_prediction_pools():
    """Lấy tổng cược để tính Odds."""
    sheet = get_worksheet()
    if not sheet: return 0, 0, 0
    try:
        total = int(sheet.acell(TOTAL_POOL_CELL).value)
        pool_a = int(sheet.acell(POOL_A_CELL).value)
        pool_b = int(sheet.acell(POOL_B_CELL).value)
        return total, pool_a, pool_b
    except:
        return 0, 0, 0