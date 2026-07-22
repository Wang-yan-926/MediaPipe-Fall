# dialogs.py
import os
import pymysql
import cv2
from PyQt6.QtWidgets import (QDialog, QLabel, QPushButton, QListWidget, QListWidgetItem, 
                             QFileDialog, QHBoxLayout, QVBoxLayout, QLineEdit, 
                             QMessageBox, QSlider, QCheckBox, QFormLayout, QTextEdit, QGridLayout, QFrame)
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QImage, QPixmap, QDesktopServices, QFont

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
                host='localhost', user='root', password='231006410',
                database='fall_detector_db', charset='utf8mb4'
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


class HistoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎬 历史跌倒告警记录与亲情处理中心")
        self.resize(1000, 560)

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
        left_layout.addWidget(self.file_list, stretch=3)

        lbl_note = QLabel("✍️ 家属处理意见与备注:")
        lbl_note.setStyleSheet("font-weight: bold; color: #38BDF8; margin-top: 5px;")
        left_layout.addWidget(lbl_note)

        self.txt_note = QTextEdit()
        self.txt_note.setPlaceholderText("请输入处理说明，例如：已电话联系老人，确认系不小心绊倒，无大碍。")
        self.txt_note.setMaximumHeight(80)
        # 强制设置输入框内文字为清晰的黑色，背景为纯白
        self.txt_note.setStyleSheet("color: #000000; background-color: #FFFFFF; font-size: 13px; border-radius: 4px; padding: 4px;")
        left_layout.addWidget(self.txt_note)

        self.btn_resolve = QPushButton("✅ 提交处理结果并标记已解决")
        self.btn_resolve.setStyleSheet("background-color: #059669; color: #FFFFFF; font-weight: bold; padding: 8px;")
        self.btn_resolve.clicked.connect(self.mark_as_resolved)
        left_layout.addWidget(self.btn_resolve)

        btn_open = QPushButton("📂 打开本地视频存档目录")
        btn_open.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(self.save_dir)))
        left_layout.addWidget(btn_open)

        main_layout.addLayout(left_layout, stretch=4)

        right_layout = QVBoxLayout()
        self.video_label = QLabel("请从左侧选择告警记录进行回放")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("background-color: #020617; border-radius: 8px; color: #64748B;")
        right_layout.addWidget(self.video_label, stretch=1)

        main_layout.addLayout(right_layout, stretch=5)

    def mark_as_resolved(self):
        current_item = self.file_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "提示", "请先在左侧列表中选择一条告警记录！")
            return
            
        file_path = current_item.data(Qt.ItemDataRole.UserRole)
        filename = os.path.basename(file_path)
        note_text = self.txt_note.toPlainText().strip()
        status_str = f"已处理: {note_text}" if note_text else "已处理 (家属已确认)"
        
        try:
            db = pymysql.connect(
                host='localhost', user='root', password='231006410',
                database='fall_detector_db', charset='utf8mb4'
            )
            cursor = db.cursor()
            cursor.execute("UPDATE alarm_logs SET status = %s WHERE video_filename = %s;", (status_str, filename))
            db.commit()
            cursor.close()
            db.close()
            
            QMessageBox.information(self, "成功", "告警状态与家属处理意见已同步至数据库！")
            self.load_logs_from_db() 
        except Exception as e:
            QMessageBox.critical(self, "错误", f"更新数据库失败: {e}")

    def load_logs_from_db(self):
        self.file_list.clear()
        try:
            db = pymysql.connect(
                host='localhost', user='root', password='231006410',
                database='fall_detector_db', charset='utf8mb4'
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
                    item_text = f"[{alarm_time}] {filename}\n状态: {status}"
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


class HealthDashboardDialog(QDialog):
    """❤️ 专属老人健康指标可视化大屏弹窗（与主界面尺寸相当，极具科技感与美观度）"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📊 智能养老 - 老人健康指标可视化监控大屏")
        self.resize(1100, 650)
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # 1. 顶部标题与左上角开发注释说明
        top_frame = QFrame()
        top_frame.setStyleSheet("background-color: #1E293B; border-radius: 8px; border: 1px solid #334155;")
        top_layout = QVBoxLayout(top_frame)
        
        title_lbl = QLabel("🏥 老人实时健康体征与多维传感可视化大屏")
        title_lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #38BDF8; border: none;")
        top_layout.addWidget(title_lbl)

        # 醒目的左上角注释说明
        note_lbl = QLabel("ℹ️ 开发注释说明：当前大屏展示的各项心率、血氧、血压及运动体征数据均为系统模拟生成。后期正式部署时，可通过 MQTT/TCP 协议无缝接入老人佩戴的智能手环、毫米波雷达等嵌入式物联网硬件设备进行实时数据采集。")
        note_lbl.setWordWrap(True)
        note_lbl.setStyleSheet("color: #94A3B8; font-size: 12px; border: none; line-height: 1.4;")
        top_layout.addWidget(note_lbl)
        
        main_layout.addWidget(top_frame)

        # 2. 中部核心卡片网格布局（2行3列）
        grid_layout = QGridLayout()
        grid_layout.setSpacing(15)

        # 卡片1：实时心率
        card_hr = self.create_metric_card("❤️ 实时心率 (Heart Rate)", "76 bpm", "状态: 正常平稳 (波形: ▂▃▅▆▇▆▅▃)", "#0284C7")
        grid_layout.addWidget(card_hr, 0, 0)

        # 卡片2：血氧饱和度
        card_spo2 = self.create_metric_card("🩸 血氧饱和度 (SpO2)", "98 %", "状态: 优良安全", "#059669")
        grid_layout.addWidget(card_spo2, 0, 1)

        # 卡片3：血压监测
        card_bp = self.create_metric_card("🩺 血压状况 (Blood Pressure)", "118 / 76 mmHg", "状态: 正常血压范围", "#7C3AED")
        grid_layout.addWidget(card_bp, 0, 2)

        # 卡片4：今日运动步数
        card_steps = self.create_metric_card("🚶 今日活动步数", "3,420 步", "目标达成率: 68% (活跃)", "#D97706")
        grid_layout.addWidget(card_steps, 1, 0)

        # 卡片5：体表温度
        card_temp = self.create_metric_card("🌡️ 实时体表温度", "36.5 ℃", "状态: 无发热迹象", "#DC2626")
        grid_layout.addWidget(card_temp, 1, 1)

        # 卡片6：智能终端设备电量
        card_battery = self.create_metric_card("🔋 穿戴设备剩余电量", "92 %", "状态: 续航充足", "#2563EB")
        grid_layout.addWidget(card_battery, 1, 2)

        main_layout.addLayout(grid_layout)

        # 3. 底部操作区
        btn_layout = QHBoxLayout()
        btn_refresh = QPushButton("🔄 刷新最新体征数据")
        btn_refresh.setStyleSheet("background-color: #334155; color: #F8FAFC; font-weight: bold; padding: 10px 20px;")
        btn_refresh.clicked.connect(lambda: QMessageBox.information(self, "刷新成功", "已向嵌入式网关发送数据同步指令，当前体征已更新！"))
        btn_layout.addWidget(btn_refresh)

        btn_layout.addStretch()

        btn_close = QPushButton("关闭大屏")
        btn_close.setStyleSheet("background-color: #475569; color: #FFFFFF; font-weight: bold; padding: 10px 20px;")
        btn_close.clicked.connect(self.accept)
        btn_layout.addWidget(btn_close)

        main_layout.addLayout(btn_layout)

    def create_metric_card(self, title, value, status, accent_color):
        card = QFrame()
        card.setStyleSheet(f"background-color: #1E293B; border-radius: 8px; border-left: 5px solid {accent_color}; border-top: 1px solid #334155; border-right: 1px solid #334155; border-bottom: 1px solid #334155;")
        layout = QVBoxLayout(card)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #94A3B8; font-size: 13px; font-weight: bold; border: none;")
        layout.addWidget(lbl_title)

        lbl_val = QLabel(value)
        lbl_val.setStyleSheet(f"color: {accent_color}; font-size: 26px; font-weight: bold; border: none; margin: 5px 0;")
        layout.addWidget(lbl_val)

        lbl_status = QLabel(status)
        lbl_status.setStyleSheet("color: #E2E8F0; font-size: 12px; border: none;")
        layout.addWidget(lbl_status)

        return card