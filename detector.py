# detector.py
import os
import math
import time
import json
import urllib.request
import numpy as np
import cv2
from collections import deque
from ultralytics import YOLO
import mediapipe as mp
from PIL import Image, ImageDraw, ImageFont
import pygame 
import pymysql
import threading
from PyQt6.QtCore import QThread, pyqtSignal, QDateTime

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

def aci_hesapla(omuz_merkezi, kalca_merkezi):
    dy = omuz_merkezi[1] - kalca_merkezi[1]
    dx = omuz_merkezi[0] - kalca_merkezi[0]
    aci = math.atan2(dy, dx)
    return abs(90 - np.degrees(aci))

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
                webhook_url, data=data, headers={'Content-Type': 'application/json'}, method='POST'
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
        try:
            self.play_alarm_sound()
            dusme_video_dosyasi = os.path.join(self.save_dir, filename)
            writer = cv2.VideoWriter(
                dusme_video_dosyasi, cv2.VideoWriter_fourcc(*'mp4v'), fps, (genislik, yukseklik)
            )
            while buffer_frames:
                writer.write(buffer_frames.popleft())
            
            self.current_async_writer = writer
            self.save_alarm_to_db(filename)
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
            min_detection_confidence=0.5, min_tracking_confidence=0.5, model_complexity=0
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