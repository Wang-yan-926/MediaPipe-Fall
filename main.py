
import sys
import os
import math
import numpy as np
import cv2
from collections import deque
from ultralytics import YOLO
import mediapipe as mp
from PIL import Image, ImageDraw, ImageFont
import pygame 

from PyQt6.QtWidgets import (QApplication, QMainWindow, QLabel, 
                             QPushButton, QFrame, QListWidgetItem, QDialog)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer, QDateTime, QUrl
from PyQt6.QtGui import QImage, QPixmap, QFont, QDesktopServices
from PyQt6.uic import loadUi


# ==================== 初始化音频模块 ====================
try:
    pygame.mixer.init()
except Exception as e:
    print(f"音频模块初始化失败: {e}")


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
    color: #F8FAFC;
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

def durus_siniflandir(torso_aci, ayakta_esik=20, yatay_esik=50):
    if torso_aci < ayakta_esik:
        return "站立 (Normal)"
    elif torso_aci > yatay_esik:
        return "平躺 (Lying)"
    else:
        return "跌倒中 (Falling)"


# ==================== 历史告警视频查看弹窗 ====================

class HistoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎬 历史跌倒告警视频回放")
        self.resize(850, 500)

        self.save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'result')
        os.makedirs(self.save_dir, exist_ok=True)

        self.cap = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)

        self.initUI()
        self.refresh_file_list()

    def initUI(self):
        from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QListWidget
        
        main_layout = QHBoxLayout(self)
        
        left_layout = QVBoxLayout()
        self.file_list = QListWidget()
        self.file_list.itemClicked.connect(self.on_file_selected)
        left_layout.addWidget(self.file_list)

        btn_open = QPushButton("📂 打开所在文件夹")
        btn_open.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self.save_dir)))
        left_layout.addWidget(btn_open)

        main_layout.addLayout(left_layout, stretch=2)

        right_layout = QVBoxLayout()
        self.video_label = QLabel("请选择视频进行回放")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("background-color: #020617; border-radius: 8px; color: #64748B;")
        right_layout.addWidget(self.video_label, stretch=1)

        main_layout.addLayout(right_layout, stretch=4)

    def refresh_file_list(self):
        self.file_list.clear()
        if os.path.exists(self.save_dir):
            files = [f for f in os.listdir(self.save_dir) if f.endswith('.mp4')]
            files.sort(reverse=True)
            for file in files:
                item = QListWidgetItem(f"📹 {file}")
                item.setData(Qt.ItemDataRole.UserRole, os.path.join(self.save_dir, file))
                self.file_list.addItem(item)

    def on_file_selected(self, item):
        file_path = item.data(Qt.ItemDataRole.UserRole)
        if not file_path or not os.path.exists(file_path):
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

    def __init__(self, source=0):
        super().__init__()
        self.source = source
        self.running = True

        self.save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'result')
        os.makedirs(self.save_dir, exist_ok=True)

        self.alarm_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'alarm.mp3')

    def stop(self):
        self.running = False
        self.wait()

    def play_alarm_sound(self):
        """播放告警音频文件"""
        try:
            if os.path.exists(self.alarm_file):
                if not pygame.mixer.music.get_busy(): # 确保上一个播完或没在播时触发
                    pygame.mixer.music.load(self.alarm_file)
                    pygame.mixer.music.play()
        except Exception as e:
            print(f"播放警报音频异常: {e}")

    def run(self):
        self.log_signal.emit("正在加载 YOLOv8 & MediaPipe 模型...")
        model = YOLO('yolov8n.pt')
        
        cap = cv2.VideoCapture(self.source)
        if not cap.isOpened():
            self.log_signal.emit("❌ 错误：无法打开指定的视频源！")
            self.running = False
            return

        self.log_signal.emit("✅ 视频源加载成功，开始监测...")

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
        was_falling = False  # 状态跟踪变量，防止连续重复触发警报音

        tampon_boyutu = 10
        kare_tamponu = deque(maxlen=tampon_boyutu)

        mp_cizim = mp.solutions.drawing_utils
        mp_poz = mp.solutions.pose

        with mp_poz.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as poz:
            while self.running and cap.isOpened():
                ret, kare = cap.read()
                if not ret:
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
                                h, w, _ = kisi_bbox.shape

                                omuzlar = [
                                    (isaretler[mp_poz.PoseLandmark.LEFT_SHOULDER.value].x * w, isaretler[mp_poz.PoseLandmark.LEFT_SHOULDER.value].y * h),
                                    (isaretler[mp_poz.PoseLandmark.RIGHT_SHOULDER.value].x * w, isaretler[mp_poz.PoseLandmark.RIGHT_SHOULDER.value].y * h)
                                ]
                                kalcalar = [
                                    (isaretler[mp_poz.PoseLandmark.LEFT_HIP.value].x * w, isaretler[mp_poz.PoseLandmark.LEFT_HIP.value].y * h),
                                    (isaretler[mp_poz.PoseLandmark.RIGHT_HIP.value].x * w, isaretler[mp_poz.PoseLandmark.RIGHT_HIP.value].y * h)
                                ]

                                omuz_merkezi = ((omuzlar[0][0] + omuzlar[1][0]) / 2, (omuzlar[0][1] + omuzlar[1][1]) / 2)
                                kalca_merkezi = ((kalcalar[0][0] + kalcalar[1][0]) / 2, (kalcalar[0][1] + kalcalar[1][1]) / 2)

                                torso_aci = aci_hesapla(kalca_merkezi, omuz_merkezi)
                                current_durus = durus_siniflandir(torso_aci)

                                if current_durus == "跌倒中 (Falling)":
                                    is_falling = True
                                    dusme_sayaci += 1
                                    dusme_sonrasi_kareler = 0

                                    # 🌟 跌倒瞬间触发语音警报
                                    if not was_falling:
                                        was_falling = True
                                        self.play_alarm_sound()

                                    if 0.1 * fps <= dusme_sayaci <= 0.5 * fps and dusme_video_yazici is None:
                                        dusme_video_sayisi += 1
                                        dusme_video_dosyasi = os.path.join(self.save_dir, f'dusme_{dusme_video_sayisi}.mp4')
                                        dusme_video_yazici = cv2.VideoWriter(
                                            dusme_video_dosyasi, cv2.VideoWriter_fourcc(*'mp4v'), fps, (genislik, yukseklik)
                                        )
                                        while kare_tamponu:
                                            dusme_video_yazici.write(kare_tamponu.popleft())
                                        
                                        self.log_signal.emit(f"⚠️ 警报：检测到人员跌倒！已保存至 result/dusme_{dusme_video_sayisi}.mp4")
                                else:
                                    dusme_sayaci = 0
                                    was_falling = False  # 恢复状态，为下一次跌倒做准备

                                if current_durus == "站立 (Normal)" and dusme_video_yazici is not None:
                                    dusme_sonrasi_kareler += 1

                            kare[y1:y2, x1:x2] = kisi_bbox

                            color = (0, 0, 255) if is_falling else (0, 255, 0)
                            cv2.rectangle(kare, (x1, y1), (x2, y2), color, 2)

                            text_pos = (x1, max(y1 - 30, 10))
                            kare = cv2_add_chinese_text(kare, current_durus, text_pos, font_size=22, color=color)

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
    def __init__(self):
        super().__init__()
        
        ui_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'diedao.ui')
        loadUi(ui_path, self)

        self.thread = None
        self.video_source = 0

        self.btn_camera.clicked.connect(self.set_camera_source)
        self.btn_file.clicked.connect(self.select_video_file)
        self.btn_start.clicked.connect(self.start_detection)
        self.btn_stop.clicked.connect(self.stop_detection)
        self.btn_history.clicked.connect(self.open_history_dialog)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_clock)
        self.timer.start(1000)

        self.add_log("系统初始化完成，等待启动指令。")

    def update_clock(self):
        now = QDateTime.currentDateTime().toString("yyyy-MM-dd hh:mm:ss")
        self.lbl_clock.setText(f"🕒 {now}")

    def add_log(self, text):
        time_str = QDateTime.currentDateTime().toString("hh:mm:ss")
        item = QListWidgetItem(f"[{time_str}] {text}")
        self.log_list.addItem(item)
        self.log_list.scrollToBottom()

    def set_camera_source(self):
        self.video_source = 0
        self.add_log("切换输入源为: 默认摄像头 (0)")

    def select_video_file(self):
        from PyQt6.QtWidgets import QFileDialog
        file_name, _ = QFileDialog.getOpenFileName(self, "选择视频文件", "", "Video Files (*.mp4 *.avi *.mov)")
        if file_name:
            self.video_source = file_name
            self.add_log(f"选择文件: {file_name.split('/')[-1]}")

    def open_history_dialog(self):
        dialog = HistoryDialog(self)
        dialog.exec()

    def start_detection(self):
        self.thread = DetectionThread(source=self.video_source)
        self.thread.change_pixmap_signal.connect(self.update_image)
        self.thread.log_signal.connect(self.add_log)
        self.thread.start()

        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self.btn_camera.setEnabled(False)
        self.btn_file.setEnabled(False)

        self.lbl_live_badge.setText("● LIVE 实时监测中")
        self.lbl_live_badge.setStyleSheet("color: #10B981; font-weight: bold; font-size: 13px; border: none;")

    def stop_detection(self):
        if self.thread is not None:
            self.thread.stop()
            self.thread = None

        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)
        self.btn_camera.setEnabled(True)
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
    window = MainWindow()
    window.show()
    sys.exit(app.exec())