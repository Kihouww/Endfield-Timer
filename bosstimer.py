import mss
import time
import tkinter as tk
from threading import Thread, Lock
import win32gui
import win32con
import ctypes

try:
    ctypes.windll.user32.SetProcessDPIAware()
except Exception:
    pass

# ==========================================
#  配置区域
# ==========================================
BOSS_CONFIGS = {
    "RHODAGN": {
        "name": "罗丹",
        "en_name": "RHODAGN",

        "lower_red": [174, 159, 226],
        "upper_red": [175, 172, 255],
        
        "rhodagn_lower_1": [10, 156, 143],
        "rhodagn_upper_1": [10, 215, 253],
        "rhodagn_lower_2": [173, 156, 143],
        "rhodagn_upper_2": [178, 215, 253],

        "finish_rect": (980, 0, 1290, 300),
        
        "finish_color_lower": [0, 190, 245],
        "finish_color_upper": [0, 205, 255],
    },
    "TRIAGGELOS": {
        "name": "三位一体",
        "en_name": "TRIAGGELOS",

        "lower_red": [174, 159, 226], 
        "upper_red": [175, 172, 255],

        "finish_rect": (980, 0, 1290, 300),

        "finish_color_lower": [0, 190, 245],
        "finish_color_upper": [0, 205, 255],
        
    },
    "MARBLE": {
        "name": "白垩界卫",
        "en_name": "MARBLE\nAGGELOMOIRAI",
        
        "lower_red": [174, 159, 226], 
        "upper_red": [175, 172, 255],

        "finish_rect": (980, 0, 1290, 300),
        
        "finish_color_lower": [0, 190, 245],
        "finish_color_upper": [0, 205, 255],
    },
    "RUANYI": {
        "name": "阮一",
        "en_name": "RUAN YI",

        "lower_red": [174, 159, 226], 
        "upper_red": [175, 172, 255],
        "finish_rect": (980, 0, 1290, 300),
        "finish_color_lower": [0, 190, 245],
        "finish_color_upper": [0, 205, 255],
    }
}

class BossTimerUnified:
    def __init__(self):
        global cv2, np
        import cv2
        import numpy as np

        # 基础通用配置
        self.TARGET_PAUSE_BGR = np.array([253, 253, 255])
        self.IS_WAIT_BGR = np.array([254,253,255])
        self.TARGET_PRE_READY_BGR = np.array([236, 236, 238])
        self.pre_ready_timestamp = 0.0

        # 状态变量
        self.running = True
        self.current_boss = "RHODAGN" # 默认加载罗丹
        self.state = "WAITING_FOR_GAME"
        self.game_found = False
        self.start_time, self.accumulated_time = 0.0, 0.0
        self.final_display_time = 0.0
        
        self.debug_ratio = 0.0
        self.lock = Lock()

        # 初始化加载
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
            # 通用参数
            self.lower_red = np.array(cfg["lower_red"])
            self.upper_red = np.array(cfg["upper_red"])
            
            if boss_key == "RHODAGN":
                self.rhodagn_l1 = np.array(cfg["rhodagn_lower_1"])
                self.rhodagn_u1 = np.array(cfg["rhodagn_upper_1"])
                self.rhodagn_l2 = np.array(cfg["rhodagn_lower_2"])
                self.rhodagn_u2 = np.array(cfg["rhodagn_upper_2"])

            if "finish_rect" in cfg:
                # 坐标计算
                base_x1, base_y1, base_x2, base_y2 = cfg["finish_rect"]
                real_left = int(base_x1 * self.ui_scale) + self.screen_left
                real_top = int(base_y1 * self.ui_scale) + self.screen_top
                real_right = int(base_x2 * self.ui_scale) + self.screen_left
                real_bottom = int(base_y2 * self.ui_scale) + self.screen_top
                    
                self.finish_monitor = {
                    "left": real_left, "top": real_top,
                    "width": max(1, real_right - real_left),
                    "height": max(1, real_bottom - real_top)
                }
                    
                # 阈值加载
                # 如果配置里有，就用配置的；如果没有，给默认值或者报错
                self.finish_lower = np.array(cfg.get("finish_color_lower", np.array([0, 197, 255])))
                self.finish_upper = np.array(cfg.get("finish_color_upper", np.array([0, 197, 255])))

                pts = np.array([
                    [0, 0], 
                    [int(10 * self.ui_scale), 0], 
                    [int(310 * self.ui_scale), int(300 * self.ui_scale)], 
                    [int(300 * self.ui_scale), int(300 * self.ui_scale)]
                ], np.int32)
                self.finish_poly_mask = np.zeros((self.finish_monitor["height"], self.finish_monitor["width"]), dtype=np.uint8)
                cv2.fillPoly(self.finish_poly_mask, [pts], 255)

                total_mask_pixels = cv2.countNonZero(self.finish_poly_mask)
                self.finish_threshold = int(total_mask_pixels * (2900 / 3000))
                    
            else:
                # 无配置时的默认空值
                self.finish_monitor = {"top": 0, "left": 0, "width": 1, "height": 1}
                self.finish_lower = np.array([0, 0, 0])
                self.finish_upper = np.array([0, 0, 0])
                self.finish_poly_mask = np.ones((1, 1), dtype=np.uint8) * 255
                self.finish_threshold = 1
                

            self.current_boss = boss_key
            self.state = "IDLE"
            self.accumulated_time = 0.0

    def calculate_regions(self):
        # 获取游戏窗口绝对坐标
        hwnd = win32gui.FindWindow(None, "Endfield")
        # 假窗口过滤
        self.game_found = False

        if hwnd and win32gui.IsWindowVisible(hwnd):
            # 剔除边框，只取纯游戏画面的绝对坐标和长宽
            left, top = win32gui.ClientToScreen(hwnd, (0, 0))
            _, _, screen_w, screen_h = win32gui.GetClientRect(hwnd)

            # 假窗口过滤
            if screen_w >= 1280:
                self.game_found = True
        else:
            # 没找到游戏时，默认抓取主显示器作为保底数据，防止程序崩溃
            with mss.mss() as sct:
                m = sct.monitors[1]
                screen_w, screen_h = m["width"], m["height"]
                left, top = m["left"], m["top"]
            self.game_found = False
            
        self.scale_x = screen_w / 2560
        self.scale_y = screen_h / 1440

        # 缩放比例计算
        self.ui_scale = min(self.scale_x, self.scale_y)

        self.screen_left = left
        self.screen_top = top
        self.screen_w = screen_w
        self.screen_h = screen_h

        def get_region(x1, y1, x2, y2):
            l = int(x1 * self.ui_scale) + left
            t = int(y1 * self.ui_scale) + top
            r = int(x2 * self.ui_scale) + left
            b = int(y2 * self.ui_scale) + top
            return {"left": l, "top": t, "width": max(1, r - l), "height": max(1, b - t)}

        bw = int(633 * self.ui_scale)
        bh = int(16 * self.ui_scale)
        self.boss_monitor = {
            "top": int(79 * self.ui_scale) + top, 
            "left": int((screen_w - bw) / 2) + left, 
            "width": bw, "height": bh
        }
        self.boss_pixels = bw * bh 
        
        self.pause_monitor = get_region(2540, 630, 2560, 900)
        self.wait_monitor = get_region(165, 175, 200, 200)
        self.pre_ready_monitor = get_region(1675, 1300, 1700, 1340)

    def setup_ui(self):
        self.root = tk.Tk()
        self.root.title("Endfield_BossTimer")
        
        # 动态布局计算
        BASE_W, BASE_H = 360, 160
        
        win_w = int(self.screen_w * (BASE_W / 2560))
        win_h = int(self.screen_h * (BASE_H / 1440))
        ui_x = int(self.screen_w * (50 / 2560)) + self.screen_left
        ui_y = int(self.screen_h * (520 / 1440)) + self.screen_top
        font_scale = min(self.scale_x, self.scale_y)
        
        def s_y(val): return int(val * self.scale_y)
        def s_x(val): return int(val * self.scale_x)

        self.root.geometry(f"{win_w}x{win_h}+{ui_x}+{ui_y}") 
        self.root.overrideredirect(True)
        
        # 背景
        self.bg_color = "#1C1C1E"
        # -transparentcolor 防止 Win11 系统的 DWM 裁切黑影伪影
        self.root.attributes("-topmost", True, "-alpha", 0.85, "-transparentcolor", "#000000")
        self.root.config(bg=self.bg_color)
        
        # Canvas
        self.canvas = tk.Canvas(self.root, bg="#010101", highlightthickness=0)
        self.canvas.place(x=0, y=0, width=win_w, height=win_h)
        
        def create_round_rect(x1, y1, x2, y2, r, **kwargs):
            points = (x1+r, y1, x1+r, y1, x2-r, y1, x2-r, y1, x2, y1, x2, y1+r, x2, y1+r, x2, y2-r, x2, y2-r, x2, y2, x2-r, y2, x2-r, y2, x1+r, y2, x1+r, y2, x1, y2, x1, y2-r, x1, y2-r, x1, y1+r, x1, y1+r, x1, y1)
            return self.canvas.create_polygon(points, **kwargs, smooth=True)
            
        create_round_rect(1, 1, win_w-1, win_h-1, s_x(15), fill=self.bg_color)

        self.divider = tk.Frame(self.root, bg="#4A4A4C", height=1)
        self.divider.place(x=0, y=s_y(45) - 1, width=win_w)

        # 拖拽
        self._drag_x = None
        self._drag_y = None
        
        # 顶部 45 像素为拖拽区
        DRAG_ZONE_HEIGHT = s_y(45)

        def start_drag(e):
            if e.y <= DRAG_ZONE_HEIGHT:
                self._drag_x = e.x
                self._drag_y = e.y
            else:
                self._drag_x = None

        def do_drag(e):
            if self._drag_x is not None:
                x = self.root.winfo_x() + (e.x - self._drag_x)
                y = self.root.winfo_y() + (e.y - self._drag_y)
                self.root.geometry(f"+{x}+{y}")

        self.canvas.bind("<ButtonPress-1>", start_drag)
        self.canvas.bind("<B1-Motion>", do_drag)

        # 控件布局
        top_bar_h = s_y(45)
        
        # 退出按钮
        f_size_close = int(12 * font_scale)
        self.btn_close = tk.Label(self.root, text="×", font=("Microsoft YaHei", f_size_close),
                                  fg="#8E8E93", bg=self.bg_color, cursor="hand2")
        self.btn_close.place(x=win_w - s_x(15), y=s_y(2), anchor="ne")

        def on_close_enter(_): self.btn_close.config(fg="#FF453A")
        def on_close_leave(_): self.btn_close.config(fg="#8E8E93")
        def on_close_click(_):
            import os
            os._exit(0)
            
        self.btn_close.bind("<Enter>", on_close_enter)
        self.btn_close.bind("<Leave>", on_close_leave)
        self.btn_close.bind("<Button-1>", on_close_click)

        # Boss 托盘下拉菜单
        f_size_menu = int(10 * font_scale)
        boss_name = BOSS_CONFIGS[self.current_boss]["name"]
        
        self.boss_menu_btn = tk.Menubutton(self.root, text=f"❖ 目标: {boss_name}", 
                                           font=("Microsoft YaHei", f_size_menu, "bold"),
                                           fg="#E5E5EA", bg=self.bg_color, 
                                           activebackground="#2C2C2E", activeforeground="#FFFFFF",
                                           cursor="hand2", relief="flat")
        self.boss_menu_btn.place(x=s_x(10), y=s_y(5), anchor="nw")

        self.boss_menu = tk.Menu(self.boss_menu_btn, tearoff=0, bg="#2C2C2E", fg="#FFFFFF", 
                                 font=("Microsoft YaHei", f_size_menu),
                                 activebackground="#0A84FF", activeforeground="#FFFFFF",
                                 relief="flat", borderwidth=0)
        self.boss_menu_btn.config(menu=self.boss_menu)
        
        for key, cfg in BOSS_CONFIGS.items():
            self.boss_menu.add_command(label=f"{cfg['name']} ({cfg['en_name']})", 
                                       command=lambda k=key: self.handle_switch(k))
            
        f_size_reset = int(10 * font_scale)
        self.btn_reset = tk.Label(self.root, text="↺ 重置计时", font=("Microsoft YaHei", f_size_reset),
                                  fg="#8E8E93", bg=self.bg_color, cursor="hand2")
        # 放置在下拉菜单右侧的逻辑标题栏安全区内
        self.btn_reset.place(x=s_x(130), y=s_y(8), anchor="nw")

        # 鼠标悬停的视觉反馈
        def on_reset_enter(_): self.btn_reset.config(fg="#E5E5EA")
        def on_reset_leave(_): self.btn_reset.config(fg="#8E8E93")
            
        self.btn_reset.bind("<Enter>", on_reset_enter)
        self.btn_reset.bind("<Leave>", on_reset_leave)
        self.btn_reset.bind("<Button-1>", lambda e: self.reset_timer())    

        # 主计时器显示
        y_time = top_bar_h 
        h_time = s_y(60)
        f_size_time = int(38 * font_scale)
        self.lbl_time = tk.Label(self.root, text="00.00", font=("Verdana", f_size_time, "bold"), fg="#FFFFFF", bg=self.bg_color)
        self.lbl_time.place(x=0, y=y_time, width=win_w, height=h_time)
        self.lbl_time.bind("<Button-1>", lambda e: self.reset_timer())
        
        # 状态与信息展示区
        y_status = y_time + h_time
        h_status = s_y(25)
        f_size_status = int(10 * font_scale)
        self.lbl_status = tk.Label(self.root, text="O N   I D L E", font=("Microsoft YaHei", f_size_status, "bold"), fg="#8E8E93", bg=self.bg_color)
        self.lbl_status.place(x=0, y=y_status, width=win_w, height=h_status)
        
        # HP 提示文字
        y_debug = y_status + h_status
        f_size_debug = int(11 * font_scale) # 字体从 8 调大到了 11
        self.lbl_debug = tk.Label(self.root, text="Waiting...", font=("Consolas", f_size_debug), fg="#FFD60A", bg=self.bg_color)
        self.lbl_debug.place(x=0, y=y_debug, width=win_w, height=s_y(25)) 

        self.root.update()  # 强制 Tkinter 立刻向系统注册并画出窗口句柄

        hwnd = win32gui.FindWindow(None, "Endfield_BossTimer")
        if hwnd:
            try:
                import ctypes
                # 读取当前图层扩展样式
                style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
                # 位清除操作：移除工具窗口属性 (使之可被枚举识别)
                style = style & ~win32con.WS_EX_TOOLWINDOW
                # 位或操作：强制注入应用窗口属性
                style = style | win32con.WS_EX_APPWINDOW
                win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, style)

                # 执行物理圆角裁切
                radius = s_x(18)
                rgn = ctypes.windll.gdi32.CreateRoundRectRgn(0, 0, win_w, win_h, radius, radius)
                ctypes.windll.user32.SetWindowRgn(hwnd, rgn, True)
            except Exception:
                pass

    def handle_switch(self, boss_key):
        """ 处理下拉菜单的切换点击 """
        self.load_boss_config(boss_key)
        
        # 核心更新：同步更改左上角菜单的主显示文字
        boss_name = BOSS_CONFIGS[boss_key]["name"]
        self.boss_menu_btn.config(text=f"❖ 目标: {boss_name}")
        
        self.update_debug_text()

    def update_debug_text(self):
        boss_name = BOSS_CONFIGS[self.current_boss]["name"]
        self.lbl_debug.config(text=f"[{boss_name}] HP: {self.debug_ratio:.1%}")

    def reposition_ui(self):
        #游戏开启后，动态将 UI 移动到对应的显示器/窗口位置
        BASE_W, BASE_H = 360, 160  # 高度匹配新 UI
        win_w = int(self.screen_w * (BASE_W / 2560))
        win_h = int(self.screen_h * (BASE_H / 1440))
        ui_x = int(self.screen_w * (50 / 2560)) + self.screen_left
        ui_y = int(self.screen_h * (520 / 1440)) + self.screen_top
        self.root.geometry(f"{win_w}x{win_h}+{ui_x}+{ui_y}")


    def reset_timer(self):
        with self.lock:
            if self.state == "WAITING_FOR_GAME":
                return
                
            self.state = "IDLE"
            self.start_time, self.accumulated_time, self.final_display_time = 0.0, 0.0, 0.0
            self.finish_counter = 0
            self.pre_ready_timestamp = 0.0

    def vision_loop(self):
        with mss.mss() as sct:
            while self.running:
                if not self.game_found:
                    self.calculate_regions()
                    if self.game_found:
                        self.load_boss_config(self.current_boss)
                        self.root.after(0, self.reposition_ui)
                        with self.lock:
                            self.state = "IDLE"
                    else:
                        with self.lock:
                            self.state = "WAITING_FOR_GAME"
                        time.sleep(1)
                        continue

                now = time.time()
                img_boss = np.array(sct.grab(self.boss_monitor))
                img_pause = np.array(sct.grab(self.pause_monitor))
                img_finish = np.array(sct.grab(self.finish_monitor))
                img_wait = np.array(sct.grab(self.wait_monitor))
                img_pre_ready = np.array(sct.grab(self.pre_ready_monitor))

                hsv_boss = cv2.cvtColor(img_boss[:,:,:3], cv2.COLOR_BGR2HSV)

                # 计算旧阈值掩膜
                mask_main = cv2.inRange(hsv_boss, self.lower_red, self.upper_red)
                
                # 如果是罗丹，叠加新阈值掩膜
                if self.current_boss == "RHODAGN":
                    mask_new_1 = cv2.inRange(hsv_boss, self.rhodagn_l1, self.rhodagn_u1)
                    mask_new_2 = cv2.inRange(hsv_boss, self.rhodagn_l2, self.rhodagn_u2)
                    # 按位或 将所有符合条件的像素合并
                    mask_main = cv2.bitwise_or(mask_main, mask_new_1)
                    mask_main = cv2.bitwise_or(mask_main, mask_new_2)

                # 计算最终比例 (red_ratio 包含了旧值和新值的所有符合像素)
                red_ratio = cv2.countNonZero(mask_main) / self.boss_pixels
                
                # 计算 pause 区域是否全为 TARGET_PAUSE_BGR (允许±4误差，防止渲染色差)
                diff_pause = np.abs(img_pause[:, :, :3].astype(int) - self.TARGET_PAUSE_BGR)
                pause_detected = np.all(diff_pause <= 4)

                diff_wait = np.abs(img_wait[:, :, :3].astype(int) - self.IS_WAIT_BGR)
                is_wait_triggered = np.all(diff_wait <= 2)

                with self.lock:
                    self.debug_ratio = red_ratio
                    
                    if self.state in ["IDLE", "FINISHED"]:
                        # 检查右下角前置条件，要求无偏差 (diff == 0)
                        diff_pre = np.abs(img_pre_ready[:, :, :3].astype(int) - self.TARGET_PRE_READY_BGR)
                        is_pre_ready = np.all(diff_pre == 0)

                        if is_pre_ready:
                            self.pre_ready_timestamp = now

                        # 0.5 秒窗口期内原逻辑通过，则强制重置计时器并切入 WAITING
                        if (now - self.pre_ready_timestamp <= 0.5) and self.pre_ready_timestamp > 0:
                            if is_wait_triggered:
                                self.start_time, self.accumulated_time, self.final_display_time = 0.0, 0.0, 0.0
                                self.finish_counter = 0 
                                self.state = "WAITING"
                                self.pre_ready_timestamp = 0.0
                            
                    elif self.state == "WAITING":
                        # 所有 Boss 统一：只要目标区域颜色不再符合（转场消失/UI变化），立刻进入 FIGHTING
                        if not is_wait_triggered:
                            self.state, self.start_time = "FIGHTING", now

                    elif self.state == "FIGHTING":
                        # [优先级 1] Finish
                        mask_finish = cv2.inRange(img_finish[:,:,:3], self.finish_lower, self.finish_upper)
                        mask_finish = cv2.bitwise_and(mask_finish, mask_finish, mask=self.finish_poly_mask)
                        if cv2.countNonZero(mask_finish) > self.finish_threshold and red_ratio < 0.05: 
                            self.final_display_time = (now - self.start_time) + self.accumulated_time - 0.22
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
        
        # 实时获取 UI 窗口位置，遮挡检测
        try:
            wx1 = self.root.winfo_x()
            wy1 = self.root.winfo_y()
            wx2 = wx1 + self.root.winfo_width()
            wy2 = wy1 + self.root.winfo_height()
            
            # 将五个核心视觉监测区打包，进行遍历遮挡检测
            monitors = [
                getattr(self, "boss_monitor", {}),
                getattr(self, "pause_monitor", {}),
                getattr(self, "finish_monitor", {}),
                getattr(self, "wait_monitor", {}),
                getattr(self, "pre_ready_monitor", {})
            ]
            
            is_overlap = False
            for m in monitors:
                if "left" not in m: continue
                mx1, my1 = m["left"], m["top"]
                mx2, my2 = mx1 + m["width"], my1 + m["height"]
                # 二维矩形相交判定公式：并非不相交，即为相交
                if not (wx2 <= mx1 or wx1 >= mx2 or wy2 <= my1 or wy1 >= my2):
                    is_overlap = True
                    break
        except Exception:
            is_overlap = False

        with self.lock:
            # 提取基础状态下的显示数据
            if self.state == "WAITING_FOR_GAME":
                t_txt, t_fg = "--.--", "#555555"
                s_txt, s_fg = "游戏未启动", "#FF4444"
            elif self.state == "IDLE":
                t_txt, t_fg = "00.00", "#555555"
                s_txt, s_fg = "I D L E", "#555555"
            elif self.state == "WAITING": 
                t_txt, t_fg = "00.00", "#FFFFFF"
                s_txt, s_fg = "READY", "#FFFFFF"
            elif self.state == "FIGHTING":
                cur = (now - self.start_time) + self.accumulated_time
                t_txt, t_fg = f"{cur:.2f}", "#FF4444"
                s_txt, s_fg = "FIGHTING", "#FF4444"
            elif self.state == "PAUSED":
                t_txt, t_fg = f"{self.accumulated_time:.2f}", "#FFD700"
                s_txt, s_fg = "P A U S E D", "#FFD700"
            elif self.state == "FINISHED":
                t_txt, t_fg = f"{self.final_display_time:.2f}", "#32CD32"
                s_txt, s_fg = "F I N I S H", "#32CD32"
            else:
                t_txt, t_fg = "--.--", "#FFFFFF"
                s_txt, s_fg = "UNKNOWN", "#FFFFFF"

            # 遮挡拦截逻辑（需求覆写） 
            if is_overlap:
                warn_msg = "拖到此处会影响计时器正常工作，换个位置吧~"
                s_fg = "#FF4444"
                
                if self.state in ["WAITING_FOR_GAME", "IDLE", "WAITING"]:
                    # 静止状态：重置数字并提示
                    t_txt = "--.--"
                    s_txt = warn_msg
                elif self.state == "FINISHED":
                    # 结算状态：保留最终成绩并提示
                    s_txt = warn_msg
                elif self.state in ["FIGHTING", "PAUSED"]:
                    # 战斗状态：计时器不受影响继续滚动，下方文字变提示
                    s_txt = warn_msg

            self.lbl_time.config(text=t_txt, fg=t_fg)
            self.lbl_status.config(text=s_txt, fg=s_fg)
            
            self.update_debug_text()
            
        self.root.after(30, self.update_ui)

    def start(self):
        self.update_ui(); self.root.mainloop()

if __name__ == "__main__":
    app = BossTimerUnified()
    app.start()