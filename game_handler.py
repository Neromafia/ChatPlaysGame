# game_handler.py
# (Chỉ cập nhật hàm get_winner_and_payout và hàm main)
# (Các hàm khác: capture_screen_region, find_template, read_winner_ocr, process_payouts, check_jackpot_win ... giữ nguyên như code trước)

import sys
import os
import pydirectinput
import cv2
import mss
import numpy as np
import json
import math
import random
import time  # Quan trọng cho việc delay
import db_manager 
import config 
import pytesseract

# (Đảm bảo đường dẫn Tesseract đã chính xác)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'

# (Các hàm OpenCV, read_winner_ocr, process_payouts, check_jackpot_win ... giữ nguyên code cũ)

# --- BỘ ĐIỀU PHỐI (ROUTER) ---
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("LỖI: Cần lệnh (start_race_prep, start_race_click, hoặc get_winner_and_payout).")
        sys.exit()

    command = sys.argv[1]
    
    if command == "start_race_prep":
        """Chuẩn bị cho vòng mới (Xóa file cược, Reset Pool)."""
        print("Chuẩn bị vòng mới: Xóa file cược cũ và reset Pool Odds...")
        if os.path.exists("current_predictions.json"):
            try:
                os.remove("current_predictions.json")
            except Exception as e:
                print(f"Không thể xóa file cược cũ: {e}")
        db_manager.reset_prediction_pools()
            
    elif command == "start_race_click":
        """Click nút 'Start Simulation' (để bắt đầu đua)."""
        print("Đang tìm nút 'Start Simulation' (start_race_button.png)...")
        screen = capture_screen_region()
        # (Bạn cần chụp ảnh nút 'Start' hoặc 'Ready' và lưu thành 'start_race_button.png')
        coords = find_template(screen, 'start_race_button.png', 0.8) 
        
        if coords:
            pydirectinput.click(coords[0], coords[1])
            print("Đã click Bắt đầu Cuộc đua (Simulation).")
            
            # --- LOGIC MỚI: CHỜ 3S VÀ NHẤN 'B' ---
            print("Chờ 3 giây để nhấn 'B' (Auto Camera)...")
            time.sleep(3.0)
            pydirectinput.press('b')
            print("Đã nhấn 'B'. Camera tự động.")
            # --- KẾT THÚC LOGIC MỚI ---
            
        else:
            print("LỖI: Không tìm thấy nút 'Start Simulation'. Thử nhấn Enter.")
            pydirectinput.press('enter') 

    elif command == "get_winner_and_payout":
        """Đọc kết quả, trả thưởng, và nhấn nút để sang vòng mới."""
        print("Đang đọc kết quả cuộc đua (Dùng OCR)...")
        winner = read_winner_ocr() 
        if winner:
            process_payouts(winner) # Xử lý trả thưởng
        else:
            # ... (Logic hủy vòng giữ nguyên) ...

        # --- LOGIC RE-QUEUE 24/7 (ĐÃ CẬP NHẬT HOÀN CHỈNH) ---
        print("Đang nhấn ESC để hiện chuột và click 'Final Results'...")
        
        pydirectinput.press('escape')
        time.sleep(0.5) # Chờ chuột hiện ra
        
        screen = capture_screen_region()
        coords_final = find_template(screen, 'final_results_button.png', 0.8)
        
        if coords_final:
            pydirectinput.click(coords_final[0], coords_final[1])
            print("Đã click 'Final Results'.")

            # --- BƯỚC MỚI: CHỜ VÀ CLICK "NEXT RACE" ---
            print("Chờ 1 giây để nút 'Next Race' xuất hiện...")
            time.sleep(1.0) # Chờ 1 giây
            
            screen_after_click = capture_screen_region()
            # (Bạn cần chụp ảnh nút 'Next Race' (hoặc 'Back to Lobby') và lưu thành 'next_race_button.png')
            coords_next = find_template(screen_after_click, 'next_race_button.png', 0.8)
            
            if coords_next:
                pydirectinput.click(coords_next[0], coords_next[1])
                print("Đã click 'Next Race'.")

                # --- BƯỚC MỚI: CHỜ VÀ CLICK "START RACE" (Vòng lặp mới) ---
                print("Chờ 2 giây để nút 'Start Race' (mới) xuất hiện...")
                time.sleep(2.0) # Chờ 2 giây
                
                screen_lobby = capture_screen_region()
                # (Dùng lại ảnh mẫu 'start_race_button.png' (hoặc 'start_simulation_button.png'))
                coords_start_new = find_template(screen_lobby, 'start_race_button.png', 0.8) 
                
                if coords_start_new:
                    pydirectinput.click(coords_start_new[0], coords_start_new[1])
                    print("Đã click Bắt đầu Cuộc đua MỚI.")
                    
                    # --- BƯỚC MỚI: CHỜ 3S VÀ NHẤN 'B' ---
                    print("Chờ 3 giây để nhấn 'B' (Auto Camera)...")
                    time.sleep(3.0)
                    pydirectinput.press('b')
                    print("Đã nhấn 'B'. Vòng lặp 24/7 hoàn tất.")
                else:
                    print("LỖI: Không tìm thấy nút 'Start Race' (mới) trong sảnh chờ.")
            else:
                print("LỖI: Không tìm thấy nút 'Next Race'.")
        else:
            print("LỖI: Không tìm thấy nút 'Final Results'. Bot có thể bị kẹt!")
    elif command == "check_status_and_start_race":
        """Chỉ chạy nếu đang ở sảnh chờ (lobby) và chưa đua."""
        print("Kiểm tra trạng thái sảnh chờ...")
        screen = capture_screen_region()
        coords_start = find_template(screen, 'start_race_button.png', 0.8)
        
        if coords_start:
            # Nếu tìm thấy nút Start, nghĩa là Bot đang ở sảnh chờ (có thể bị kẹt)
            print("Phát hiện Bot đang ở sảnh chờ. Bắt đầu cuộc đua (Dự phòng)...")
            pydirectinput.click(coords_start[0], coords_start[1])
            time.sleep(3.0)
            pydirectinput.press('b')
            
            # Ngay lập tức mở cược (Vì Main Loop của Streamer.bot không còn nữa)
            # Bạn cần gọi hàm Open Betting của Streamer.bot (qua Webhook)
            # HOẶC: Chuyển toàn bộ logic Timer vào Python
        else:
            # Bot đang trong cuộc đua hoặc đang ở màn hình kết quả, không cần làm gì
            print("Bot đang chạy (Đang đua hoặc Đang xử lý kết quả). Bỏ qua.")