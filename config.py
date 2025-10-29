# config.py - File cấu hình trung tâm

import math

# --- API & DATABASE ---
# (Các file .json này phải nằm chung thư mục)
CLIENT_SECRETS_FILE = "client_secret.json" 
SERVICE_ACCOUNT_FILE = 'service_account_key.json' 
TOKEN_PICKLE_FILE = "token.pickle" # Sẽ được tự động tạo

# Google Sheet Database Names (Phải khớp 100%)
SPREADSHEET_NAME = 'LIVE DATABASE' 
WORKSHEET_NAME = 'USERDATA' 

# Cột DB (Thứ tự phải khớp Google Sheet Hàng 1)
DB_COLS = {
    "ID": 1, "USERNAME": 2, "POINTS": 3, "EXP": 4, 
    "LEVEL": 5, "KEYS": 6, "INVENTORY": 7, "DATE_JOINED": 8,
    "LAST_SEEN": 9, "MEMBER_TIER": 10 # Thêm 2 cột mới
}
# Giả định ô A1 của Sheet 'USERDATA' dùng để lưu Quỹ Chung
JACKPOT_CELL = 'K1' 
# Giả định ô B1 dùng để lưu tổng cược (cho Odds)
TOTAL_POOL_CELL = 'L1'
POOL_A_CELL = 'M1'
POOL_B_CELL = 'N1'


# --- KINH TẾ & LEVEL (Đã chốt) ---
# Cày chay
POINTS_PER_5_MIN = 1.0 # Điểm (P) cơ bản (sẽ được nhân)
EXP_PER_MINUTE = 1 # 1 EXP cho mỗi phút xem live

# Hệ số nhân cho Hội viên (Members) - Cần khớp với YouTube
MEMBER_MULTIPLIERS = {
    "default": 1.0, # Người Sub (Cấp 1)
    "level_2": 1.5, # Cấp 2
    "level_3": 2.0, # Cấp 3
    "level_4": 5.0, # Cấp 4
    "level_5": 10.0 # Cấp 5 (Đại Tướng)
    # Thêm tên Cấp bậc (Tier Name) chính xác từ YouTube Studio của bạn vào đây
}

# Nạp tiền (Tỷ giá)
USD_TO_VND_RATE = 25500 # Tỷ giá (ví dụ)
# 1 USD SuperChat (Net 70%) = 120 Points (P)
POINTS_PER_USD_SC = 120
# 1 USD MoMo/PayPal (Net 97%) = 180 Points (P)
POINTS_PER_USD_DIRECT = 180
# Mua EXP (Tỷ lệ MoMo/PayPal)
EXP_PER_VND_DIRECT = 0.05 # 10k VND = 500 EXP (500/10000)
# Mua Key (Tỷ lệ SuperChat/PayPal)
KEYS_PER_USD_SC = 4.0 # 1 USD SC = 4 Keys (Net 70%)
KEYS_PER_USD_DIRECT = 5.0 # 1 USD Direct = 5 Keys
# EXP thưởng khi mua Key/Points
BASE_EXP_PER_KEY_PURCHASED = 100 # 1 Key nạp tiền thật = 100 EXP

# Leveling (Base 100, Multi 1.0239)
LEVEL_BASE = 100
LEVEL_MULTIPLIER = 1.0239 # (Mốc ~100tr VNĐ Lvl 300)

# --- DỰ ĐOÁN (PREDICTION) ---
MIN_PREDICTION = 20 # Điểm tối thiểu
MAX_PREDICTION_PERCENTAGE = 0.20 # 20%
EXP_PER_POINT_COMMITTED = 1 # 1 Điểm dự đoán = 1 EXP
EXP_WIN_BONUS_PER_LEVEL = 0.01 # Thắng cược nhận thêm 1% EXP mỗi Level

# --- QUỸ THƯỞNG CHUNG (COMMUNITY POOL) ---
POOL_CONTRIBUTION_RATE = 0.10 # 10% (Bot tài trợ)
MIN_POOL_FOR_CHECK = 100000 # Pool phải đạt 100k
POOL_WIN_BASE_CHANCE = 0.0005 # 0.05%
POOL_WIN_LEVEL_BONUS_PER_LEVEL = 0.00002 # 0.002%

# --- LOOT BOX (GACHA) ---
LOOT_TABLE = {
    'VIP_5_LIFETIME': 0.005,   # 0.5% - Jackpot: VIP Vĩnh Viễn
    'X2_PAYOUT_TICKET': 0.05,  # 5.0% - Vé nhân đôi
    'INSURANCE_TICKET': 0.25,  # 25.0% - Vé bảo hiểm
    'EXP_LARGE': 0.10,         # 10.0% (500 EXP)
    'EXP_MEDIUM': 0.20,        # 20.0% (150 EXP)
    'EXP_SMALL': 0.30,         # 30.0% (50 EXP)
    'POINTS_JACKPOT': 0.01,    # 1.0% (5000 Points)
    'POINTS_SMALL_DROP': 0.085 # 8.5% (100 Points)
}