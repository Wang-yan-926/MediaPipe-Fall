import sys
import os
import math
import time
import json
import urllib.request
import urllib.parse
import numpy as np
import cv2
from collections import deque
from ultralytics import YOLO
import mediapipe as mp
from PIL import Image, ImageDraw, ImageFont
import pygame 
import pymysql
import threading  # 引入多线程库用于异步告警处理
from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, 
                             QPushButton, QFrame, QListWidget, QListWidgetItem, QDialog, 
                             QFileDialog, QHBoxLayout, QVBoxLayout, QComboBox,
                             QLineEdit, QMessageBox, QSlider, QCheckBox, QFormLayout)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer, QDateTime, QUrl
from PyQt6.QtGui import QImage, QPixmap, QFont, QDesktopServices
from PyQt6.uic import loadUi


# ==================== 初始化音频模块 ====================
try:
    pygame.mixer.init()
except Exception as e:
    print(f"音频模块初始化失败: {e}")


# ==================== 数据库连接与初始化工具 ====================

def init_database():
    """自动初始化 MySQL 数据库与基础表结构"""
    try:
        conn = pymysql.connect(
            host='localhost',
            user='root',
            password='231006410',
            charset='utf8mb4'
        )
        cursor = conn.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS fall_detector_db DEFAULT CHARACTER SET utf8mb4;")
        cursor.close()
        conn.close()

        db = pymysql.connect(
            host='localhost',
            user='root',
            password='231006410',
            database='fall_detector_db',
            charset='utf8mb4'
        )
        cursor = db.cursor()

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL UNIQUE,
            password VARCHAR(100) NOT NULL,
            role VARCHAR(20) NOT NULL
        );
        """)

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS alarm_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            alarm_time VARCHAR(50),
            video_filename VARCHAR(255),
            status VARCHAR(50)
        );
        """)

        cursor.execute("SELECT COUNT(*) FROM users WHERE username='root';")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO users (username, password, role) VALUES ('root', '231006410', 'admin');")
            cursor.execute("INSERT INTO users (username, password, role) VALUES ('family', '123456', 'family');")
            db.commit()

        cursor.close()
        db.close()
        print("✅ MySQL 数据库连接及初始化成功！")
        return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False


# ==================== 全局主题样式表 ====================

STYLE_SHEET = """
QMainWindow, QDialog {
    background-color: #0F172A;
}

QWidget {
    color: #F8FAFC;
    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
}

QPushButton {
    background-color: #334155;
    border: 1px solid #475569;
    border-radius: 6px;
    color: #FFFFFF;
    font-size: 13px;
    font-weight: 600;
    padding: 8px 14px;
}
QPushButton:hover {
    background-color: #475569;
    border-color: #64748B;
}
QPushButton:pressed {
    background-color: #1E293B;
}
QPushButton:disabled {
    background-color: #1E293B;
    border-color: #334155;
    color: #64748B;
}

QComboBox, QLineEdit {
    background-color: #334155;
    border: 1px solid #475569;
    border-radius: 6px;
    color: #FFFFFF;
    font-size: 13px;
    padding: 6px 10px;
}
QComboBox:hover, QLineEdit:hover {
    border-color: #64748B;
}
QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 25px;
    border-left-width: 1px;
    border-left-color: #475569;
    border-left-style: solid;
}
QComboBox QAbstractItemView {
    background-color: #1E293B;
    color: #F8FAFC;
    selection-background-color: #334155;
    border: 1px solid #475569;
}

QListWidget {
    background-color: #0F172A;
    border: 1px solid #334155;
    border-radius: 6px;
    color: #CBD5E1;
    font-size: 13px;
    padding: 5px;
}
QListWidget::item {
    padding: 6px;
    border-bottom: 1px solid #1E293B;
}

QSlider::groove:horizontal {
    border: 1px solid #475569;
    height: 6px;
    background: #1E293B;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #38BDF8;
    border: 1px solid #0284C7;
    width: 16px;
    margin: -5px 0;
    border-radius: 8px;
}
QSlider::handle:horizontal:hover {
    background: #7DD3FC;
}
"""


# ==================== 中文绘制辅助函数 ====================

def cv2_add_chinese_text(img, text, position, font_size=20, color=(0, 255, 0)):
    img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)

    try:
        font = ImageFont.truetype("msyh.ttc", font_size)
    except OSError:
        try:
            font = ImageFont.truetype("simhei.ttf", font_size)
        except OSError:
            font = ImageFont.load_default()

    rgb_color = (color[2], color[1], color[0])
    draw.text(position, text, font=font, fill=rgb_color)
    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)


# ==================== 跌倒检测算法辅助函数 ====================

def aci_hesapla(omuz_merkezi, kalca_merkezi):
    dy = omuz_merkezi[1] - kalca_merkezi[1]
    dx = omuz_merkezi[0] - kalca_merkezi[0]
    aci = math.atan2(dy, dx)
    return abs(90 - np.degrees(aci))


# ==================== 1. 登录验证弹窗 ====================

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🔐 系统身份验证 (MySQL版)")
        self.resize(360, 230)
        self.user_role = None  
        self.logged_username = None

        layout = QVBoxLayout(self)

        title_label = QLabel("智能跌倒检测与看护系统")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #38BDF8; margin-bottom: 10px;")
        layout.addWidget(title_label)

        form_layout = QFormLayout()
        
        self.txt_user = QLineEdit()
        self.txt_user.setPlaceholderText("请输入账户名 (如: root)")
        self.txt_user.setText("root")  
        form_layout.addRow("账    号:", self.txt_user)

        self.txt_pass = QLineEdit()
        self.txt_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_pass.setPlaceholderText("请输入密码")
        self.txt_pass.setText("231006410")  
        form_layout.addRow("密    码:", self.txt_pass)

        layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        btn_login = QPushButton("登录系统")
        btn_login.clicked.connect(self.handle_login)
        btn_layout.addWidget(btn_login)

        btn_cancel = QPushButton("退出")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)

    def handle_login(self):
        username = self.txt_user.text().strip()
        password = self.txt_pass.text().strip()

        try:
            db = pymysql.connect(
                host='localhost',
                user='root',
                password='231006410',
                database='fall_detector_db',
                charset='utf8mb4'
            )
            cursor = db.cursor()
            cursor.execute("SELECT role FROM users WHERE username=%s AND password=%s;", (username, password))
            result = cursor.fetchone()
            cursor.close()
            db.close()

            if result:
                self.user_role = result[0]  
                self.logged_username = username
                self.accept()
            else:
                QMessageBox.warning(self, "登录失败", "用户名或密码错误，请检查 MySQL 中的凭证！")
        except Exception as e:
            QMessageBox.critical(self, "数据库错误", f"无法连接到 MySQL 数据库:\n{e}")


# ==================== 2. 系统设置弹窗 ====================

class SettingsDialog(QDialog):
    def __init__(self, current_settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ 系统高级参数与飞书机器人设置")
        self.resize(600, 340)
        self.settings = current_settings.copy()
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.slider_angle = QSlider(Qt.Orientation.Horizontal)
        self.slider_angle.setRange(30, 70)
        self.slider_angle.setValue(self.settings.get("fall_threshold", 50))
        self.lbl_angle_val = QLabel(f"{self.slider_angle.value()} °")
        self.slider_angle.valueChanged.connect(lambda v: self.lbl_angle_val.setText(f"{v} °"))
        
        angle_layout = QHBoxLayout()
        angle_layout.addWidget(self.slider_angle)
        angle_layout.addWidget(self.lbl_angle_val)
        form_layout.addRow("跌倒倾斜角阈值:", angle_layout)

        self.chk_sound = QCheckBox("启用声音告警 (alarm.mp3)")
        self.chk_sound.setChecked(self.settings.get("sound_enabled", True))
        form_layout.addRow("声 音 告 警:", self.chk_sound)

        self.slider_buffer = QSlider(Qt.Orientation.Horizontal)
        self.slider_buffer.setRange(3, 20)
        self.slider_buffer.setValue(self.settings.get("buffer_seconds", 10))
        self.lbl_buffer_val = QLabel(f"{self.slider_buffer.value()} 秒")
        self.slider_buffer.valueChanged.connect(lambda v: self.lbl_buffer_val.setText(f"{v} 秒"))

        buffer_layout = QHBoxLayout()
        buffer_layout.addWidget(self.slider_buffer)
        buffer_layout.addWidget(self.lbl_buffer_val)
        form_layout.addRow("录制前置缓冲区:", buffer_layout)

        self.txt_webhook = QLineEdit()
        self.txt_webhook.setPlaceholderText("请输入飞书机器人 Webhook 链接")
        self.txt_webhook.setText("https://open.feishu.cn/open-apis/bot/v2/hook/e1d06cee-2c38-4679-962a-9fccb85fd766")
        self.txt_webhook.setReadOnly(True)  
        form_layout.addRow("飞书Webhook:", self.txt_webhook)

        layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        btn_save = QPushButton("保存配置")
        btn_save.clicked.connect(self.save_settings)
        btn_layout.addWidget(btn_save)

        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        layout.addLayout(btn_layout)

    def save_settings(self):
        self.settings["fall_threshold"] = self.slider_angle.value()
        self.settings["sound_enabled"] = self.chk_sound.isChecked()
        self.settings["buffer_seconds"] = self.slider_buffer.value()
        self.settings["feishu_webhook"] = "https://open.feishu.cn/open-apis/bot/v2/hook/e1d06cee-2c38-4679-962a-9fccb85fd766"
        self.accept()


# ==================== 历史告警视频回放弹窗 ====================

class HistoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎬 历史跌倒告警记录与回放")
        self.resize(900, 500)

        self.save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'result')
        os.makedirs(self.save_dir, exist_ok=True)

        self.cap = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)

        self.initUI()
        self.load_logs_from_db()

    def initUI(self):
        main_layout = QHBoxLayout(self)
        
        left_layout = QVBoxLayout()
        self.file_list = QListWidget()
        self.file_list.itemClicked.connect(self.on_file_selected)
        left_layout.addWidget(self.file_list)

        btn_open = QPushButton("📂 打开视频文件夹")
        btn_open.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self.save_dir)))
        left_layout.addWidget(btn_open)

        main_layout.addLayout(left_layout, stretch=3)

        right_layout = QVBoxLayout()
        self.video_label = QLabel("请从左侧选择告警记录进行回放")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("background-color: #020617; border-radius: 8px; color: #64748B;")
        right_layout.addWidget(self.video_label, stretch=1)

        main_layout.addLayout(right_layout, stretch=4)

    def load_logs_from_db(self):
        self.file_list.clear()
        try:
            db = pymysql.connect(
                host='localhost',
                user='root',
                password='231006410',
                database='fall_detector_db',
                charset='utf8mb4'
            )
            cursor = db.cursor()
            cursor.execute("SELECT id, alarm_time, video_filename, status FROM alarm_logs ORDER BY id DESC;")
            records = cursor.fetchall()
            cursor.close()
            db.close()

            for row in records:
                log_id, alarm_time, filename, status = row
                file_path = os.path.join(self.save_dir, filename)
                
                if os.path.exists(file_path):
                    item_text = f"[{alarm_time}] {filename} ({status})"
                    item = QListWidgetItem(item_text)
                    item.setData(Qt.ItemDataRole.UserRole, file_path)
                    self.file_list.addItem(item)
                else:
                    try:
                        cleanup_db = pymysql.connect(
                            host='localhost', user='root', password='231006410',
                            database='fall_detector_db', charset='utf8mb4'
                        )
                        c = cleanup_db.cursor()
                        c.execute("DELETE FROM alarm_logs WHERE id = %s;", (log_id,))
                        cleanup_db.commit()
                        c.close()
                        cleanup_db.close()
                    except:
                        pass

        except Exception as e:
            print(f"从数据库读取历史失败: {e}")

    def on_file_selected(self, item):
        file_path = item.data(Qt.ItemDataRole.UserRole)
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(self, "文件缺失", f"在本地磁盘中未找到该视频文件:\n{file_path}")
            return

        if self.cap is not None:
            self.cap.release()

        self.cap = cv2.VideoCapture(file_path)
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        interval = int(1000 / fps) if fps > 0 else 33
        self.timer.start(interval)

    def update_frame(self):
        if self.cap is not None and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = frame_rgb.shape
                qt_img = QImage(frame_rgb.data, w, h, ch * w, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(qt_img)
                self.video_label.setPixmap(
                    pixmap.scaled(self.video_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                )
            else:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

    def closeEvent(self, event):
        self.timer.stop()
        if self.cap is not None:
            self.cap.release()
        event.accept()




# ==================== 后台检测线程 ====================

class DetectionThread(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray, str, int, bool)
    log_signal = pyqtSignal(str)

    def __init__(self, source=0, settings=None):
        super().__init__()
        self.source = source
        default_webhook = "https://open.feishu.cn/open-apis/bot/v2/hook/e1d06cee-2c38-4679-962a-9fccb85fd766"
        self.settings = settings if settings else {"fall_threshold": 50, "sound_enabled": True, "buffer_seconds": 10, "feishu_webhook": default_webhook}
        self.settings["feishu_webhook"] = default_webhook
            
        self.running = True

        self.save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'result')
        os.makedirs(self.save_dir, exist_ok=True)
        self.alarm_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'alarm.mp3')
        
        self.last_feishu_time = 0 

    def stop(self):
        self.running = False
        self.wait()

    def play_alarm_sound(self):
        if not self.settings.get("sound_enabled", True):
            return
        try:
            if os.path.exists(self.alarm_file):
                if not pygame.mixer.music.get_busy():
                    pygame.mixer.music.load(self.alarm_file)
                    pygame.mixer.music.play()
        except Exception as e:
            print(f"播放警报音频异常: {e}")

    def send_feishu_notification(self, video_filename):
        webhook_url = "https://open.feishu.cn/open-apis/bot/v2/hook/e1d06cee-2c38-4679-962a-9fccb85fd766"
        time_str = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
        
        payload = {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {"tag": "plain_text", "content": "🚨 紧急警报：智能看护系统检测到跌倒！"},
                    "template": "red"
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": f"**⚠️ 注意：监控画面检测到老人发生跌倒行为！**\n\n"
                                       f"- **发生时间**：`{time_str}`\n"
                                       f"- **录像存档**：`{video_filename}`\n"
                                       f"- **系统状态**：已自动截取前后缓冲区视频保存至本地，并将告警事件记录成功写入 MySQL 数据库。"
                        }
                    },
                    {
                        "tag": "note",
                        "elements": [{"tag": "plain_text", "content": "请家属立刻查看监控或通过历史回访确认老人安全！"}]
                    }
                ]
            }
        }

        data = json.dumps(payload).encode('utf-8')

        try:
            req = urllib.request.Request(
                webhook_url, 
                data=data, 
                headers={'Content-Type': 'application/json'}, 
                method='POST'
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                result = json.loads(response.read().decode('utf-8'))
                if result.get('code') == 0 or result.get('StatusCode') == 0:
                    self.log_signal.emit("✅ 飞书机器人跌倒告警实时推送成功！")
                else:
                    self.log_signal.emit(f"⚠️ 飞书推送返回错误: {result}")
        except Exception as e:
            self.log_signal.emit(f"❌ 发送飞书通知异常: {e}")

    def save_alarm_to_db(self, filename):
        try:
            db = pymysql.connect(
                host='localhost', user='root', password='231006410',
                database='fall_detector_db', charset='utf8mb4'
            )
            cursor = db.cursor()
            time_str = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
            cursor.execute(
                "INSERT INTO alarm_logs (alarm_time, video_filename, status) VALUES (%s, %s, %s);",
                (time_str, filename, "未处理")
            )
            db.commit()
            cursor.close()
            db.close()
        except Exception as e:
            print(f"写入数据库告警记录失败: {e}")

    def handle_alarm_async(self, filename, buffer_frames, fps, genislik, yukseklik):
        """🚀 核心优化：将耗时的写视频、连数据库、发网络请求、播音乐放在独立子线程执行，防止主界面卡顿"""
        try:
            # 1. 播放声音
            self.play_alarm_sound()

            # 2. 写入视频文件（包含前置缓冲区）
            dusme_video_dosyasi = os.path.join(self.save_dir, filename)
            writer = cv2.VideoWriter(
                dusme_video_dosyasi, cv2.VideoWriter_fourcc(*'mp4v'), fps, (genislik, yukseklik)
            )
            while buffer_frames:
                writer.write(buffer_frames.popleft())
            
            # 暂存 writer 引用以便后续主循环继续写入后续跌倒画面
            self.current_async_writer = writer

            # 3. 写入数据库
            self.save_alarm_to_db(filename)

            # 4. 发送飞书网络请求
            self.send_feishu_notification(filename)
            
            self.log_signal.emit(f"⚠️ 警报：检测到人员跌倒！已异步存入本地与MySQL、推送飞书并保存至 {filename}")
        except Exception as e:
            self.log_signal.emit(f"❌ 异步处理告警异常: {e}")

    def run(self):
        self.log_signal.emit("正在加载 YOLOv8 & MediaPipe 模型 (已启用轻量极速与异步告警模式)...")
        try:
            model = YOLO('yolov8n.pt')
        except Exception as e:
            self.log_signal.emit(f"❌ YOLO 模型加载失败: {e}")
            return
        
        cap_source = int(self.source) if str(self.source).isdigit() else self.source
        cap = cv2.VideoCapture(cap_source)
        
        if not cap.isOpened():
            self.log_signal.emit(f"❌ 错误：无法打开视频源 [{self.source}]！")
            return

        self.log_signal.emit(f"✅ 成功连接视频源: {self.source}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0 or math.isnan(fps):
            fps = 30.0

        genislik = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        yukseklik = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        dusme_sayaci = 0
        dusme_video_sayisi = 0
        dusme_sonrasi_kareler = 0
        dusme_sonrasi_bekleme_suresi = 10
        dusme_video_yazici = None
        self.current_async_writer = None
        
        last_alarm_timestamp = 0
        cooldown_seconds = 1  

        buffer_sec = self.settings.get("buffer_seconds", 10)
        tampon_boyutu = int(buffer_sec * fps)
        kare_tamponu = deque(maxlen=tampon_boyutu)

        mp_cizim = mp.solutions.drawing_utils
        mp_poz = mp.solutions.pose
        fall_threshold = self.settings.get("fall_threshold", 50)

        with mp_poz.Pose(
            min_detection_confidence=0.5, 
            min_tracking_confidence=0.5,
            model_complexity=0
        ) as poz:
            while self.running and cap.isOpened():
                ret, kare = cap.read()
                if not ret:
                    if not str(self.source).isdigit():
                        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        continue
                    else:
                        self.log_signal.emit("⚠️ 摄像头读取中断或无数据。")
                        break

                current_durus = "未检测到人员"
                is_falling = False

                sonuclar = model(kare, verbose=False)
                for sonuc in sonuclar:
                    for bbox, sinif in zip(sonuc.boxes.xyxy, sonuc.boxes.cls):
                        if int(sinif) == 0:  
                            x1, y1, x2, y2 = map(int, bbox)
                            x1, y1 = max(0, x1), max(0, y1)
                            x2, y2 = min(genislik, x2), min(yukseklik, y2)
                            
                            if x2 - x1 < 10 or y2 - y1 < 10:
                                continue

                            kisi_bbox = kare[y1:y2, x1:x2].copy()
                            kisi_bbox_rgb = cv2.cvtColor(kisi_bbox, cv2.COLOR_BGR2RGB)
                            kisi_sonuclari = poz.process(kisi_bbox_rgb)

                            if kisi_sonuclari.pose_landmarks:
                                mp_cizim.draw_landmarks(
                                    kisi_bbox, kisi_sonuclari.pose_landmarks, mp_poz.POSE_CONNECTIONS
                                )

                                isaretler = kisi_sonuclari.pose_landmarks.landmark
                                h_box, w_box, _ = kisi_bbox.shape

                                omuzlar = [
                                    (isaretler[mp_poz.PoseLandmark.LEFT_SHOULDER.value].x * w_box, isaretler[mp_poz.PoseLandmark.LEFT_SHOULDER.value].y * h_box),
                                    (isaretler[mp_poz.PoseLandmark.RIGHT_SHOULDER.value].x * w_box, isaretler[mp_poz.PoseLandmark.RIGHT_SHOULDER.value].y * h_box)
                                ]
                                kalcalar = [
                                    (isaretler[mp_poz.PoseLandmark.LEFT_HIP.value].x * w_box, isaretler[mp_poz.PoseLandmark.LEFT_HIP.value].y * h_box),
                                    (isaretler[mp_poz.PoseLandmark.RIGHT_HIP.value].x * w_box, isaretler[mp_poz.PoseLandmark.RIGHT_HIP.value].y * h_box)
                                ]

                                omuz_merkezi = ((omuzlar[0][0] + omuzlar[1][0]) / 2, (omuzlar[0][1] + omuzlar[1][1]) / 2)
                                kalca_merkezi = ((kalcalar[0][0] + kalcalar[1][0]) / 2, (kalcalar[0][1] + kalcalar[1][1]) / 2)

                                torso_aci = aci_hesapla(kalca_merkezi, omuz_merkezi)
                                
                                if torso_aci < 20:
                                    current_durus = "站立 (Normal)"
                                elif torso_aci > fall_threshold:
                                    current_durus = "平躺 (Lying)"
                                else:
                                    current_durus = "跌倒中 (Falling)"

                                if current_durus == "跌倒中 (Falling)":
                                    is_falling = True
                                    dusme_sayaci += 1
                                    dusme_sonrasi_kareler = 0

                                    current_time = time.time()
                                    if 1 <= dusme_sayaci and (current_time - last_alarm_timestamp > cooldown_seconds):
                                        if dusme_video_yazici is None and self.current_async_writer is None:
                                            last_alarm_timestamp = current_time  
                                            dusme_video_sayisi += 1
                                            filename = f'dusme_{QDateTime.currentDateTime().toString("yyyyMMdd_hhmmss")}_{dusme_video_sayisi}.mp4'
                                            
                                            # 🚀 开启独立子线程异步处理文件写入与网络请求，保证当前帧顺畅通过
                                            buffer_copy = deque(kare_tamponu)
                                            alarm_thread = threading.Thread(
                                                target=self.handle_alarm_async,
                                                args=(filename, buffer_copy, fps, genislik, yukseklik)
                                            )
                                            alarm_thread.daemon = True
                                            alarm_thread.start()
                                else:
                                    dusme_sayaci = 0

                                if current_durus == "站立 (Normal)" and (dusme_video_yazici is not None or self.current_async_writer is not None):
                                    dusme_sonrasi_kareler += 1

                            kare[y1:y2, x1:x2] = kisi_bbox

                            color = (0, 0, 255) if is_falling else (0, 255, 0)
                            cv2.rectangle(kare, (x1, y1), (x2, y2), color, 2)

                            text_pos = (x1, max(y1 - 30, 10))
                            kare = cv2_add_chinese_text(kare, current_durus, text_pos, font_size=22, color=color)

                # 同步获取异步创建好的 VideoWriter 句柄
                if self.current_async_writer is not None:
                    dusme_video_yazici = self.current_async_writer
                    self.current_async_writer = None

                if dusme_video_yazici is not None:
                    dusme_video_yazici.write(kare)

                if dusme_sonrasi_kareler > dusme_sonrasi_bekleme_suresi and dusme_video_yazici is not None:
                    dusme_video_yazici.release()
                    dusme_video_yazici = None
                    self.log_signal.emit("ℹ️ 跌倒事件视频片段记录完毕。")

                kare_tamponu.append(kare.copy())
                self.change_pixmap_signal.emit(kare, current_durus, dusme_video_sayisi, is_falling)

        cap.release()
        if dusme_video_yazici is not None:
            dusme_video_yazici.release()
        self.log_signal.emit("⏹ 视频流已关闭。")

# ==================== PyQt6 主界面 ====================

class MainWindow(QMainWindow):
    def __init__(self, user_role="admin", username="root"):
        super().__init__()
        self.user_role = user_role  
        self.username = username

        self.current_settings = {
            "fall_threshold": 50,
            "sound_enabled": True,
            "buffer_seconds": 10,
            "feishu_webhook": "https://open.feishu.cn/open-apis/bot/v2/hook/e1d06cee-2c38-4679-962a-9fccb85fd766"
        }
        
        ui_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'diedao.ui')
        loadUi(ui_path, self)

        role_str = "【管理员】" if self.user_role == "admin" else "【普通家属端】"
        self.setWindowTitle(f"智能跌倒检测与看护系统 {role_str} - 当前用户: {self.username}")

        self.thread = None
        self.video_source = 0  

        self.setup_camera_combobox()

        self.btn_file.clicked.connect(self.select_video_file)
        self.btn_start.clicked.connect(self.start_detection)
        self.btn_stop.clicked.connect(self.stop_detection)
        self.btn_history.clicked.connect(self.open_history_dialog)

        self.setup_extra_buttons()
        self.apply_role_permissions()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_clock)
        self.timer.start(1000)

        self.add_log(f"系统启动成功，已连接 MySQL 数据库 (当前用户: {self.username})")

    def setup_extra_buttons(self):
        parent_layout = self.btn_history.parent().layout()
        if parent_layout is not None:
            self.btn_settings = QPushButton("⚙️ 系统高级设置")
            self.btn_settings.clicked.connect(self.open_settings_dialog)
            
            self.btn_switch_user = QPushButton("🔄 切换账号身份")
            self.btn_switch_user.setStyleSheet("background-color: #475569; color: #38BDF8;")
            self.btn_switch_user.clicked.connect(self.switch_account)

            index = parent_layout.indexOf(self.btn_history)
            parent_layout.insertWidget(index + 1, self.btn_settings)
            parent_layout.insertWidget(index + 2, self.btn_switch_user)

    def switch_account(self):
        if self.thread is not None and self.thread.isRunning():
            reply = QMessageBox.question(
                self, "正在监测中", 
                "当前正在进行实时视频监测，切换身份将停止监测。是否继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
            self.stop_detection()

        self.hide()

        login_dlg = LoginDialog(self)
        if login_dlg.exec() == QDialog.DialogCode.Accepted:
            new_role = login_dlg.user_role
            new_uname = login_dlg.logged_username
            
            self.new_window = MainWindow(user_role=new_role, username=new_uname)
            self.new_window.show()
            self.close()
        else:
            self.show()

    def apply_role_permissions(self):
        if self.user_role == "family":
            if hasattr(self, 'btn_settings'):
                self.btn_settings.setEnabled(False)
                self.btn_settings.setToolTip("权限不足：只有管理员账户可以修改系统设置参数！")
            self.add_log("提示：当前为家属权限，高级设置功能已被锁定。")

    def setup_camera_combobox(self):
        parent_layout = self.btn_camera.parent().layout()
        if parent_layout is not None:
            index = parent_layout.indexOf(self.btn_camera)
            parent_layout.removeWidget(self.btn_camera)
            self.btn_camera.deleteLater()

            self.camera_combo = QComboBox()
            available_cams = 0
            for i in range(4):
                cap = cv2.VideoCapture(i, cv2.CAP_DSHOW if os.name == 'nt' else cv2.CAP_ANY)
                if cap.isOpened():
                    ret, _ = cap.read()
                    if ret:
                        if i == 0:
                            cam_name = "📹 摄像头 0 (iVCam / 虚拟或首选设备)"
                        elif i == 1:
                            cam_name = "📹 摄像头 1 (电脑内置摄像头 / 外接)"
                        else:
                            cam_name = f"📹 摄像头 {i} (外接设备)"
                            
                        self.camera_combo.addItem(cam_name, i)
                        available_cams += 1
                    cap.release()

            if available_cams == 0:
                self.camera_combo.addItem("⚠️ 未检测到可用摄像头", 0)

            self.camera_combo.currentIndexChanged.connect(self.on_camera_changed)
            
            if index != -1:
                parent_layout.insertWidget(index, self.camera_combo)
            else:
                parent_layout.addWidget(self.camera_combo)

    def on_camera_changed(self, index):
        data = self.camera_combo.currentData()
        if data is not None:
            self.video_source = data
            self.add_log(f"已切换视频输入源 -> 摄像头索引 [{data}]")

    def update_clock(self):
        self.lbl_clock.setText(f"🕒 {QDateTime.currentDateTime().toString('yyyy-MM-dd hh:mm:ss')}")

    def add_log(self, text):
        time_str = QDateTime.currentDateTime().toString("hh:mm:ss")
        item = QListWidgetItem(f"[{time_str}] {text}")
        self.log_list.addItem(item)
        self.log_list.scrollToBottom()

    def select_video_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "选择视频文件", "", "Video Files (*.mp4 *.avi *.mov)")
        if file_name:
            self.video_source = file_name
            self.add_log(f"已选择本地测试视频: {file_name.split('/')[-1]}")

    def open_history_dialog(self):
        dialog = HistoryDialog(self)
        dialog.exec()

    def open_settings_dialog(self):
        if self.user_role != "admin":
            QMessageBox.warning(self, "权限拒绝", "您当前是以普通家属身份登录，无法修改系统参数！")
            return

        dialog = SettingsDialog(self.current_settings, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.current_settings = dialog.settings
            self.add_log("⚙️ 系统设置已更新: 飞书Webhook已强制绑定")
            QMessageBox.information(self, "设置成功", "高级参数已成功更新！若正在监测，请重新点击“开始监测”生效。")

    def start_detection(self):
        if self.thread is not None and self.thread.isRunning():
            return
            
        self.thread = DetectionThread(source=self.video_source, settings=self.current_settings)
        self.thread.change_pixmap_signal.connect(self.update_image)
        self.thread.log_signal.connect(self.add_log)
        self.thread.start()

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        if hasattr(self, 'camera_combo'):
            self.camera_combo.setEnabled(False)
        self.btn_file.setEnabled(False)

        self.lbl_live_badge.setText("● LIVE 实时监测中")
        self.lbl_live_badge.setStyleSheet("color: #10B981; font-weight: bold; font-size: 13px; border: none;")

    def stop_detection(self):
        if self.thread is not None:
            self.thread.stop()
            self.thread = None

        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        if hasattr(self, 'camera_combo'):
            self.camera_combo.setEnabled(True)
        self.btn_file.setEnabled(True)

        self.video_label.setText("检测已停止")
        self.lbl_live_badge.setText("● 已停止")
        self.lbl_live_badge.setStyleSheet("color: #64748B; font-weight: bold; font-size: 13px; border: none;")

        self.lbl_alarm_status.setText("系统待命")
        self.alarm_card.setStyleSheet("background-color: #0F172A; border: 1px solid #1E293B; border-radius: 8px;")
        self.lbl_alarm_status.setStyleSheet("color: #38BDF8; border: none;")
        self.add_log("监测线程已被停止。")

    def update_image(self, cv_img, durus, fall_count, is_falling):
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        
        convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(convert_to_Qt_format)
        
        self.video_label.setPixmap(
            pixmap.scaled(self.video_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        )

        self.lbl_posture.setText(f"姿态: {durus}")
        self.lbl_fall_count.setText(f"跌倒告警: {fall_count} 次")

        if is_falling:
            self.lbl_alarm_status.setText("🚨 警报：检测到人员跌倒！")
            self.lbl_alarm_status.setStyleSheet("color: #FFFFFF; border: none;")
            self.alarm_card.setStyleSheet("background-color: #DC2626; border-radius: 8px;")
        else:
            self.lbl_alarm_status.setText("🟢 画面监测正常")
            self.lbl_alarm_status.setStyleSheet("color: #10B981; border: none;")
            self.alarm_card.setStyleSheet("background-color: #022C22; border: 1px solid #065F46; border-radius: 8px;")

    def closeEvent(self, event):
        self.stop_detection()
        event.accept()


# ==================== 程序运行入口 ====================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE_SHEET)

    if not init_database():
        sys.exit(1)

    login_dlg = LoginDialog()
    if login_dlg.exec() == QDialog.DialogCode.Accepted:
        role = login_dlg.user_role
        uname = login_dlg.logged_username
        window = MainWindow(user_role=role, username=uname)
        window.show()
        sys.exit(app.exec())
    else:
        sys.exit(0)