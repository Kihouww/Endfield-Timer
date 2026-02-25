import mss
import time
import tkinter as tk
from threading import Thread, Lock
import win32gui
import win32con

# ==========================================
#  配置区域
# ==========================================
BOSS_CONFIGS = {
    "RHODAGN": {
        "name": "罗丹",
        "en_name": "RHODAGN",
        # ... (原有的 hsv 阈值保持不变) ...
        "lower_red": [174, 159, 226],
        "upper_red": [175, 172, 255],
        
        # ... (原有的罗丹第二套阈值保持不变) ...
        "rhodagn_lower_1": [10, 156, 143],
        "rhodagn_upper_1": [10, 215, 253],
        "rhodagn_lower_2": [173, 156, 143],
        "rhodagn_upper_2": [178, 215, 253],

        # === 新增：罗丹 FINISH 判定配置 ===
        # 2K基准坐标: 左上(1266, 285) - 右下(1288, 307)
        "finish_rect": (1266, 285, 1288, 307),
        
        # 颜色阈值 BGR格式 (对应 RGB: 255, 190-200, 0)
        # OpenCV 是 BGR，所以是 [0, 190, 255]
        "finish_color_lower": [0, 190, 245],
        "finish_color_upper": [0, 205, 255],
    },
    "TRIAGGELOS": {
        "name": "三位一体",
        "en_name": "TRIAGGELOS",
        # === 战斗中血条阈值 (保持不变) ===
        "lower_red": [174, 159, 226], 
        "upper_red": [175, 172, 255],
        
        # 2K基准坐标: 左上(1266, 285) - 右下(1288, 307)
        "finish_rect": (1266, 285, 1288, 307),
        
        # 颜色阈值 BGR格式 (对应 RGB: 255, 190-200, 0)
        # OpenCV 是 BGR，所以是 [0, 190, 255]
        "finish_color_lower": [0, 190, 245],
        "finish_color_upper": [0, 205, 255],
        
    },
    "MARBLE": {
        "name": "白垩界卫",
        "en_name": "MARBLE\nAGGELOMOIRAI",
        # (假设白垩界卫逻辑同罗丹，如有不同请自行修改)
        "lower_red": [174, 159, 226], 
        "upper_red": [175, 172, 255],

        # 2K基准坐标: 左上(1266, 285) - 右下(1288, 307)
        "finish_rect": (1266, 285, 1288, 307),
        
        # 颜色阈值 BGR格式 (对应 RGB: 255, 190-200, 0)
        # OpenCV 是 BGR，所以是 [0, 190, 255]
        "finish_color_lower": [0, 190, 245],
        "finish_color_upper": [0, 205, 255],
    }
}

class BossTimerUnified:
    def __init__(self):
        global cv2, np
        import cv2
        import numpy as np

        # === 基础通用配置 ===
        self.TARGET_PAUSE_BGR = np.array([253, 253, 255])
        self.IS_WAIT_BGR = np.array([254,253,255])

        # === 状态变量 ===
        self.running = True
        self.current_boss = "RHODAGN" # 默认加载罗丹
        self.state = "IDLE"             
        self.start_time, self.accumulated_time = 0.0, 0.0
        self.final_display_time = 0.0
        
        self.debug_ratio = 0.0
        self.lock = Lock()

        # === 初始化加载 ===
        self.calculate_regions()
        # 加载默认BOSS配置
        self.load_boss_config("RHODAGN")
        
        self.setup_ui()
        
        self.cv_thread = Thread(target=self.vision_loop)
        self.cv_thread.daemon = True
        self.cv_thread.start()

    def load_boss_config(self, boss_key):
        cfg = BOSS_CONFIGS[boss_key]
        with self.lock:
            # 1. 通用参数
            self.lower_red = np.array(cfg["lower_red"])
            self.upper_red = np.array(cfg["upper_red"])
            
            if boss_key == "RHODAGN":
                self.rhodagn_l1 = np.array(cfg["rhodagn_lower_1"])
                self.rhodagn_u1 = np.array(cfg["rhodagn_upper_1"])
                self.rhodagn_l2 = np.array(cfg["rhodagn_lower_2"])
                self.rhodagn_u2 = np.array(cfg["rhodagn_upper_2"])

            if "finish_rect" in cfg:
                # 1. 坐标计算
                base_x1, base_y1, base_x2, base_y2 = cfg["finish_rect"]
                real_left = int(base_x1 * self.scale_y) + self.screen_left
                real_top = int(base_y1 * self.scale_y) + self.screen_top
                real_right = int(base_x2 * self.scale_y) + self.screen_left
                real_bottom = int(base_y2 * self.scale_y) + self.screen_top
                    
                self.finish_monitor = {
                    "left": real_left, "top": real_top,
                    "width": max(1, real_right - real_left),
                    "height": max(1, real_bottom - real_top)
                }
                    
                # 2. 阈值加载 (强制加载，不再依赖 if)
                # 如果配置里有，就用配置的；如果没有，给默认值或者报错
                self.finish_lower = np.array(cfg.get("finish_color_lower", np.array([0, 190, 255])))
                self.finish_upper = np.array(cfg.get("finish_color_upper", np.array([0, 200, 255])))
                    
            else:
                # 无配置时的默认空值
                self.finish_monitor = {"top": 0, "left": 0, "width": 1, "height": 1}
                self.finish_lower = np.array([0, 0, 0])
                self.finish_upper = np.array([0, 0, 0])

            self.current_boss = boss_key
            self.state = "IDLE"
            self.accumulated_time = 0.0

    def calculate_regions(self):
        with mss.mss() as sct:
            m = sct.monitors[1]
            screen_w, screen_h = m["width"], m["height"]
            left, top = m["left"], m["top"]
            
            # 1. === 关键修改：计算全局缩放比例 (基准 2560x1440) ===
            self.scale_x = screen_w / 2560
            self.scale_y = screen_h / 1440
            
            # 保存屏幕偏移量，给 load_boss_config 用
            self.screen_left = left
            self.screen_top = top
            self.screen_w = screen_w # UI设置还需要用到这个
            self.screen_h = screen_h

            # 2. 定义辅助函数 (利用计算好的比例)
            def get_region(x1, y1, x2, y2):
                # x1, y1, x2, y2 均为 2K 分辨率下的原始坐标
                l = int(x1 * self.scale_y) + left
                t = int(y1 * self.scale_y) + top
                r = int(x2 * self.scale_y) + left
                b = int(y2 * self.scale_y) + top
                return {"left": l, "top": t, "width": max(1, r - l), "height": max(1, b - t)}

            # 3. 计算通用区域 (Boss血条、黄条、暂停图标等)
            # 注意：这里直接填 2K 下的坐标即可，函数会自动缩放
            
            # Boss 血条 (特殊居中逻辑)
            bw = int(633 * self.scale_y)
            bh = int(16 * self.scale_y)
            self.boss_monitor = {
                "top": int(79 * self.scale_y) + top, 
                "left": int((screen_w - bw) / 2) + left, 
                "width": bw, "height": bh
            }
            self.boss_pixels = bw * bh 
            
            # 暂停图标 (2540, 630) -> (2560, 900)
            self.pause_monitor = get_region(2540, 630, 2560, 900)

            # 开战检测
            self.wait_monitor = get_region(165, 175, 200, 200)

    def setup_ui(self):
        self.root = tk.Tk()
        self.root.title("Endfield_BossTimer")
        
        # === 1. 动态布局计算 ===
        # 基础设计分辨率：2560x1440
        BASE_W, BASE_H = 580, 230
        
        # 计算实际窗口大小
        win_w = int(self.screen_w * (BASE_W / 2560))
        win_h = int(self.screen_h * (BASE_H / 1440))
        
        # 计算UI位置
        ui_x = int(self.screen_w * (50 / 2560)) + self.screen_left
        ui_y = int(self.screen_h * (520 / 1440)) + self.screen_top
        
        # 字体缩放系数
        font_scale = min(self.scale_x, self.scale_y)
        
        # 辅助函数
        def s_y(val): return int(val * self.scale_y)
        def s_x(val): return int(val * self.scale_x)

        self.root.geometry(f"{win_w}x{win_h}+{ui_x}+{ui_y}") 
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True, "-transparentcolor", "#010101")
        self.root.config(bg="#010101")
        self.root.bind("<Button-1>", lambda e: self.reset_timer())

        # === 2. 控件布局 ===
        
        # [时间显示] 
        h_time = s_y(80) 
        f_size_time = int(36 * font_scale)
        self.lbl_time = tk.Label(self.root, text="00.00", font=("Verdana", f_size_time, "bold"), fg="#FFFFFF", bg="#010101")
        self.lbl_time.place(x=0, y=0, width=win_w, height=h_time)
        
        # [状态显示]
        y_status = h_time
        h_status = s_y(30)
        f_size_status = int(10 * font_scale)
        self.lbl_status = tk.Label(self.root, text="O N   I D L E", font=("Verdana", f_size_status, "bold"), fg="#444444", bg="#010101")
        self.lbl_status.place(x=0, y=y_status, width=win_w, height=h_status)
        
        # [Debug信息]
        y_debug = y_status + h_status
        h_debug = s_y(25)
        f_size_debug = int(8 * font_scale)
        self.lbl_debug = tk.Label(self.root, text="Waiting...", font=("Consolas", f_size_debug, "bold"), fg="#FFFF00", bg="#010101")
        self.lbl_debug.place(x=0, y=y_debug, width=win_w, height=h_debug)

        # [按钮栏区域]
        y_btn = y_debug + h_debug
        h_btn = s_y(65)
        
        # 字体定义
        f_size_cn = int(13 * font_scale)
        f_size_en = int(7 * font_scale) 
        f_size_sep = int(12 * font_scale)
        
        # 外部容器 (占满整行)
        btn_frame_outer = tk.Frame(self.root, bg="#010101")
        btn_frame_outer.place(x=0, y=y_btn, width=win_w, height=h_btn)
        
        # 内部容器 (绝对居中)
        inner_frame = tk.Frame(btn_frame_outer, bg="#010101")
        inner_frame.place(relx=0.5, rely=0.5, anchor="center")

        # 定义高级按钮
        def create_btn(parent, boss_key):
            cfg = BOSS_CONFIGS[boss_key]
            
            # === 核心修复：指定每个按钮容器的固定宽度 ===
            # 130 是基准宽度，防止文字挤在一起，也不会像之前那么宽
            fixed_w = s_x(130) 
            fixed_h = h_btn
            
            # 创建定宽容器，并关闭自动收缩 (pack_propagate(0))
            container = tk.Frame(parent, bg="#010101", cursor="hand2", width=fixed_w, height=fixed_h)
            container.pack_propagate(0) # 禁止子元素改变容器大小
            container.pack(side="left", padx=s_x(5)) # 按钮之间的间距
            
            # 2. 中文名 (上方)
            lbl_cn = tk.Label(container, text=cfg['name'], font=("SimHei", f_size_cn, "bold"), 
                              fg="#888888", bg="#010101", cursor="hand2")
            # y=s_y(5) 稍微往下一点点，留出呼吸感
            lbl_cn.place(relx=0.5, y=s_y(5), anchor="n") 
            
            # 3. 英文名 (下方)
            lbl_en = tk.Label(container, text=cfg['en_name'], font=("Verdana", f_size_en, "bold"), 
                              fg="#555555", bg="#010101", cursor="hand2")
            # y=s_y(28) 紧贴中文名下方
            lbl_en.place(relx=0.5, y=s_y(28), anchor="n") 
            
            # 4. 绑定事件
            widgets = [container, lbl_cn, lbl_en]
            
            def on_click(e):
                self.handle_switch(boss_key)
            def on_enter(e):
                lbl_cn.config(fg="#FFFFFF")
                lbl_en.config(fg="#AAAAAA")
            def on_leave(e):
                lbl_cn.config(fg="#888888")
                lbl_en.config(fg="#555555")

            for w in widgets:
                w.bind("<Button-1>", on_click)
                w.bind("<Enter>", on_enter)
                w.bind("<Leave>", on_leave)
                
            return container

        create_btn(inner_frame, "RHODAGN")
        tk.Label(inner_frame, text="|", font=("SimHei", f_size_sep), fg="#333333", bg="#010101").pack(side="left")
        create_btn(inner_frame, "TRIAGGELOS")
        tk.Label(inner_frame, text="|", font=("SimHei", f_size_sep), fg="#333333", bg="#010101").pack(side="left")
        create_btn(inner_frame, "MARBLE")

        # [成功提示]
        y_msg = y_btn + h_btn
        h_msg = s_y(25)
        self.lbl_msg = tk.Label(self.root, text="", font=("SimHei", f_size_status, "bold"), fg="#32CD32", bg="#010101")
        self.lbl_msg.place(x=0, y=y_msg, width=win_w, height=h_msg)

        # 退出按钮ui
        f_size_close = int(10 * font_scale)
        self.btn_close = tk.Label(self.root, text=" × ", font=("Verdana", f_size_close),
                                  fg = "#AAAAAA", bg = "#333333", cursor = "hand2")
        self.btn_close.place(x = s_x(60), y = s_y(15), anchor = "nw")

        def on_close_enter(_):
            self.btn_close.config(bg = "#FF4444", fg = "#FFFFFF")
        def on_close_leave(_):
            self.btn_close.config(bg = "#333333", fg = "#AAAAAA")
        def on_close_click(_):
            import os
            os._exit(0)

        self.btn_close.bind("<Enter>", on_close_enter)
        self.btn_close.bind("<Leave>", on_close_leave)
        self.btn_close.bind("<Button-1>", on_close_click)

        hwnd = win32gui.FindWindow(None, "Endfield_BossTimer")
        if hwnd:
            try:
                win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED)
            except Exception:
                pass

    def handle_switch(self, boss_key):
        """ 处理按钮点击 """
        self.load_boss_config(boss_key)
        # 显示绿色提示
        self.lbl_msg.config(text="切换成功！")
        # 2秒后清空提示
        self.root.after(2000, lambda: self.lbl_msg.config(text=""))
        # 强制更新一下当前显示的 BOSS 名字到 Debug 栏
        self.update_debug_text()

    def update_debug_text(self):
        boss_name = BOSS_CONFIGS[self.current_boss]["name"]
        self.lbl_debug.config(text=f"[{boss_name}] HP: {self.debug_ratio:.1%}")

    def reset_timer(self):
        with self.lock:
            self.state = "IDLE"
            self.start_time, self.accumulated_time, self.final_display_time = 0.0, 0.0, 0.0

    def vision_loop(self):
        with mss.mss() as sct:
            while self.running:
                if self.state == "FINISHED":
                    time.sleep(0.1); continue

                now = time.time()
                img_boss = np.array(sct.grab(self.boss_monitor))
                img_pause = np.array(sct.grab(self.pause_monitor))
                img_finish = np.array(sct.grab(self.finish_monitor))
                img_wait = np.array(sct.grab(self.wait_monitor))

                hsv_boss = cv2.cvtColor(img_boss[:,:,:3], cv2.COLOR_BGR2HSV)

                # 1. 计算旧阈值掩膜
                mask_main = cv2.inRange(hsv_boss, self.lower_red, self.upper_red)
                
                # 2. 如果是罗丹，叠加新阈值掩膜
                if self.current_boss == "RHODAGN":
                    mask_new_1 = cv2.inRange(hsv_boss, self.rhodagn_l1, self.rhodagn_u1)
                    mask_new_2 = cv2.inRange(hsv_boss, self.rhodagn_l2, self.rhodagn_u2)
                    # 使用按位或 (OR) 将所有符合条件的像素合并
                    mask_main = cv2.bitwise_or(mask_main, mask_new_1)
                    mask_main = cv2.bitwise_or(mask_main, mask_new_2)

                # 3. 计算最终比例 (此时 red_ratio 包含了旧值和新值的所有符合像素)
                red_ratio = cv2.countNonZero(mask_main) / self.boss_pixels
                
                # 计算 pause 区域是否全为 TARGET_PAUSE_BGR (允许±4误差，防止渲染色差)
                diff_pause = np.abs(img_pause[:, :, :3].astype(int) - self.TARGET_PAUSE_BGR)
                pause_detected = np.all(diff_pause <= 4)

                diff_wait = np.abs(img_wait[:, :, :3].astype(int) - self.IS_WAIT_BGR)
                is_wait_triggered = np.all(diff_wait <= 2)

                with self.lock:
                    self.debug_ratio = red_ratio
                    
                    if self.state == "IDLE":
                        # 所有 Boss 统一：只要监测到目标区域符合颜色，进入 WAITING
                        if is_wait_triggered:
                            self.state = "WAITING"
                            
                    elif self.state == "WAITING":
                        # 所有 Boss 统一：只要目标区域颜色不再符合（转场消失/UI变化），立刻进入 FIGHTING
                        if not is_wait_triggered:
                            self.state, self.start_time = "FIGHTING", now

                    elif self.state == "FIGHTING":
                        # [优先级 1] Finish
                        mask_finish = cv2.inRange(img_finish[:,:,:3], self.finish_lower, self.finish_upper)
                        if cv2.countNonZero(mask_finish) > 20: 
                            raw = (now - self.start_time) + self.accumulated_time
                            self.final_display_time = raw - 1.17
                            self.state = "FINISHED"

                        # [优先级 2] Pause
                        elif pause_detected:
                            self.accumulated_time += (now - self.start_time)
                            self.state = "PAUSED"
                            
                    elif self.state == "PAUSED" and not pause_detected:
                        self.start_time, self.state = now, "FIGHTING"
                            
                time.sleep(0.005)

    def update_ui(self):
        now = time.time()
        with self.lock:
            if self.state == "IDLE":
                self.lbl_status.config(text="O N   I D L E", fg="#444444")
                self.lbl_time.config(text="00.00", fg="#444444")
            elif self.state == "FIGHTING":
                cur = (now - self.start_time) + self.accumulated_time
                self.lbl_time.config(text=f"{cur:.2f}", fg="#FF4444")
                self.lbl_status.config(text="FIGHTING", fg="#FF4444")
            elif self.state == "PAUSED":
                self.lbl_time.config(text=f"{self.accumulated_time:.2f}", fg="#FFD700")
                self.lbl_status.config(text="P A U S E D", fg="#FFD700")
            elif self.state == "FINISHED":
                self.lbl_time.config(text=f"{self.final_display_time:.2f}", fg="#32CD32")
                self.lbl_status.config(text="F I N I S H", fg="#32CD32")
            elif self.state == "WAITING":
                self.lbl_status.config(text="READY", fg="#FFFFFF")
                self.lbl_time.config(text="00.00", fg="#FFFFFF")
            
            self.update_debug_text()
            
        self.root.after(30, self.update_ui)

    def start(self):
        self.update_ui(); self.root.mainloop()

if __name__ == "__main__":
    app = BossTimerUnified()
    app.start()