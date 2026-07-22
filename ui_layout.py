# ui_layout.py
from PyQt6.QtWidgets import (QWidget, QLabel, QPushButton, QFrame, 
                             QListWidget, QHBoxLayout, QVBoxLayout, QSizePolicy, QComboBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1280, 800)
        MainWindow.setWindowTitle("AI Vision Guardian - 智能人员跌倒实时监测系统")
        
        # 全局 One Dark 现代暗黑科技风样式表
        MainWindow.setStyleSheet("""
            QMainWindow {
                background-color: #1E222A;
            }
            QLabel {
                font-family: 'Microsoft YaHei', 'Segoe UI';
                color: #ABB2BF;
            }
            /* 左侧侧边栏统一的所有按钮样式（扁平纯文字风） */
            QPushButton.sidebar_btn {
                background-color: transparent;
                border: none;
                border-radius: 6px;
                color: #ABB2BF;
                text-align: left;
                padding: 10px 14px;
                font-family: 'Microsoft YaHei';
                font-size: 14px;
                font-weight: 500;
            }
            QPushButton.sidebar_btn:hover {
                background-color: #2C313C;
                color: #61AFEF;
            }
            QPushButton.sidebar_btn:pressed {
                background-color: #3E4452;
            }
            /* 右侧主工作区的通用按钮样式 */
            QPushButton {
                background-color: #21252B;
                border: 1px solid #3E4452;
                border-radius: 6px;
                color: #ABB2BF;
                padding: 8px 14px;
                font-family: 'Microsoft YaHei';
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #2C313C;
                border-color: #61AFEF;
                color: #61AFEF;
            }
            QPushButton:pressed {
                background-color: #1E222A;
            }
            QPushButton:disabled {
                background-color: #1E222A;
                color: #5C6370;
                border: 1px solid #282C34;
            }
            QComboBox {
                background-color: #21252B;
                border: 1px solid #3E4452;
                border-radius: 6px;
                color: #ABB2BF;
                font-size: 13px;
                font-weight: 600;
                padding: 6px 10px;
                font-family: 'Microsoft YaHei';
            }
            QComboBox:hover {
                border-color: #61AFEF;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 24px;
                border-left-width: 1px;
                border-left-color: #3E4452;
                border-left-style: solid;
            }
            QComboBox QAbstractItemView {
                background-color: #21252B;
                color: #ABB2BF;
                selection-background-color: #2C313C;
                selection-color: #61AFEF;
                border: 1px solid #3E4452;
                font-size: 13px;
                padding: 4px;
            }
        """)

        self.centralwidget = QWidget(MainWindow)
        
        # 主横向布局：左侧菜单栏 + 右侧主工作区
        horizontalLayout_main = QHBoxLayout(self.centralwidget)
        horizontalLayout_main.setSpacing(0)
        horizontalLayout_main.setContentsMargins(0, 0, 0, 0)

        # ==================== 1. 左侧侧边栏 (Sidebar) ====================
        self.sidebar_frame = QFrame(self.centralwidget)
        self.sidebar_frame.setFixedWidth(230)
        self.sidebar_frame.setStyleSheet("""
            QFrame {
                background-color: #21252B;
                border-right: 1px solid #181A1F;
            }
        """)
        verticalLayout_sidebar = QVBoxLayout(self.sidebar_frame)
        verticalLayout_sidebar.setSpacing(8)
        verticalLayout_sidebar.setContentsMargins(12, 16, 12, 16)

        # 侧边栏标题
        self.sidebar_title = QLabel("ONE DARK", self.sidebar_frame)
        self.sidebar_title.setFont(QFont("Microsoft YaHei", 14, QFont.Weight.Bold))
        self.sidebar_title.setStyleSheet("color: #61AFEF; padding-left: 6px; border: none;")
        verticalLayout_sidebar.addWidget(self.sidebar_title)

        # 间隔线
        line_sidebar = QFrame(self.sidebar_frame)
        line_sidebar.setFrameShape(QFrame.Shape.HLine)
        line_sidebar.setStyleSheet("background-color: #282C34; border: none; max-height: 1px; margin: 4px 0;")
        verticalLayout_sidebar.addWidget(line_sidebar)

        # 菜单按钮
        self.btn_menu_home = QPushButton("实时监控", self.sidebar_frame)
        self.btn_menu_home.setProperty("class", "sidebar_btn")
        verticalLayout_sidebar.addWidget(self.btn_menu_home)

        # 摄像头选择下拉框
        self.camera_combo = QComboBox(self.sidebar_frame)
        self.camera_combo.addItem("摄像头 0 (默认)")
        verticalLayout_sidebar.addWidget(self.camera_combo)
        self.btn_camera = self.camera_combo 

        self.btn_file = QPushButton("导入视频", self.sidebar_frame)
        self.btn_file.setProperty("class", "sidebar_btn")
        verticalLayout_sidebar.addWidget(self.btn_file)

        self.btn_history = QPushButton("历史片段", self.sidebar_frame)
        self.btn_history.setProperty("class", "sidebar_btn")
        verticalLayout_sidebar.addWidget(self.btn_history)

        # 弹簧将底部按钮推到底端
        verticalLayout_sidebar.addStretch()

        # 底部两个按钮（无 emoji 纯文字扁平风）
        self.btn_settings = QPushButton("系统高级设置", self.sidebar_frame)
        self.btn_settings.setProperty("class", "sidebar_btn")
        verticalLayout_sidebar.addWidget(self.btn_settings)

        self.btn_account = QPushButton("切换账号", self.sidebar_frame)
        self.btn_account.setProperty("class", "sidebar_btn")
        verticalLayout_sidebar.addWidget(self.btn_account)

        horizontalLayout_main.addWidget(self.sidebar_frame)

        # ==================== 2. 右侧主内容区域 ====================
        self.right_container = QWidget(self.centralwidget)
        verticalLayout_right_container = QVBoxLayout(self.right_container)
        verticalLayout_right_container.setSpacing(12)
        verticalLayout_right_container.setContentsMargins(16, 16, 16, 16)

        # 顶部栏
        self.header_frame = QFrame(self.right_container)
        self.header_frame.setStyleSheet("""
            QFrame {
                background-color: #21252B;
                border: 1px solid #282C34;
                border-radius: 8px;
            }
        """)
        horizontalLayout_header = QHBoxLayout(self.header_frame)
        horizontalLayout_header.setContentsMargins(20, 12, 20, 12)

        self.title_label = QLabel("管理平台 - 智能人员跌倒实时监测系统", self.header_frame)
        self.title_label.setFont(QFont("Microsoft YaHei", 13, QFont.Weight.Bold))
        self.title_label.setStyleSheet("color: #E5C07B; border: none;")
        horizontalLayout_header.addWidget(self.title_label)

        horizontalLayout_header.addStretch()

        self.lbl_clock = QLabel("--:--:--", self.header_frame)
        self.lbl_clock.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        self.lbl_clock.setStyleSheet("color: #98C379; border: none;")
        horizontalLayout_header.addWidget(self.lbl_clock)

        verticalLayout_right_container.addWidget(self.header_frame)

        # 中间内容区 (左侧视频 + 右侧控制面板)
        horizontalLayout_content = QHBoxLayout()
        horizontalLayout_content.setSpacing(16)

        # 左侧：视频区域卡片
        self.video_card = QFrame(self.right_container)
        self.video_card.setStyleSheet("""
            QFrame {
                background-color: #21252B;
                border: 1px solid #282C34;
                border-radius: 8px;
            }
        """)
        verticalLayout_video = QVBoxLayout(self.video_card)
        verticalLayout_video.setContentsMargins(10, 10, 10, 10)
        verticalLayout_video.setSpacing(6)

        horizontalLayout_vheader = QHBoxLayout()
        self.lbl_live_badge = QLabel("未启动监控", self.video_card)
        self.lbl_live_badge.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        self.lbl_live_badge.setStyleSheet("color: #5C6370; border: none;")
        horizontalLayout_vheader.addWidget(self.lbl_live_badge)
        horizontalLayout_vheader.addStretch()
        verticalLayout_video.addLayout(horizontalLayout_vheader)

        self.video_label = QLabel("请选择视频源，点击右侧【启动检测】", self.video_card)
        self.video_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.video_label.setStyleSheet("background-color: #181A1F; border-radius: 6px; color: #528BFF; font-size: 14px; border: none;")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        verticalLayout_video.addWidget(self.video_label)

        horizontalLayout_content.addWidget(self.video_card, stretch=5)

        # 右侧：控制面板与指标卡片
        self.control_card = QFrame(self.right_container)
        self.control_card.setMaximumWidth(380)
        self.control_card.setStyleSheet("""
            QFrame {
                background-color: #21252B;
                border: 1px solid #282C34;
                border-radius: 8px;
            }
        """)
        verticalLayout_control = QVBoxLayout(self.control_card)
        verticalLayout_control.setSpacing(12)
        verticalLayout_control.setContentsMargins(16, 16, 16, 16)

        self.ctrl_title = QLabel("操作与控制台", self.control_card)
        self.ctrl_title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        self.ctrl_title.setStyleSheet("color: #61AFEF; border: none;")
        verticalLayout_control.addWidget(self.ctrl_title)

        horizontalLayout_btn_group = QHBoxLayout()
        horizontalLayout_btn_group.setSpacing(10)
        
        self.btn_start = QPushButton("启动检测", self.control_card)
        self.btn_start.setStyleSheet("""
            QPushButton {
                background-color: #98C379;
                color: #21252B;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #88B369;
            }
        """)
        horizontalLayout_btn_group.addWidget(self.btn_start)

        self.btn_stop = QPushButton("停止检测", self.control_card)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("""
            QPushButton {
                background-color: #E06C75;
                color: #21252B;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #D05C65;
            }
            QPushButton:disabled {
                background-color: #282C34;
                color: #5C6370;
            }
        """)
        horizontalLayout_btn_group.addWidget(self.btn_stop)
        verticalLayout_control.addLayout(horizontalLayout_btn_group)

        line1 = QFrame(self.control_card)
        line1.setFrameShape(QFrame.Shape.HLine)
        line1.setStyleSheet("background-color: #282C34; border: none; max-height: 1px;")
        verticalLayout_control.addWidget(line1)

        self.stat_title = QLabel("实时监控指标", self.control_card)
        self.stat_title.setFont(QFont("Microsoft YaHei", 12, QFont.Weight.Bold))
        self.stat_title.setStyleSheet("color: #61AFEF; border: none;")
        verticalLayout_control.addWidget(self.stat_title)

        self.alarm_card = QFrame(self.control_card)
        self.alarm_card.setStyleSheet("background-color: #181A1F; border: 1px solid #282C34; border-radius: 6px;")
        verticalLayout_alarm = QVBoxLayout(self.alarm_card)
        verticalLayout_alarm.setContentsMargins(8, 8, 8, 8)
        
        self.lbl_alarm_status = QLabel("系统待命", self.alarm_card)
        self.lbl_alarm_status.setFont(QFont("Microsoft YaHei", 13, QFont.Weight.Bold))
        self.lbl_alarm_status.setStyleSheet("color: #61AFEF; border: none;")
        self.lbl_alarm_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        verticalLayout_alarm.addWidget(self.lbl_alarm_status)
        verticalLayout_control.addWidget(self.alarm_card)

        horizontalLayout_subdata = QHBoxLayout()
        self.lbl_posture = QLabel("姿态: --", self.control_card)
        self.lbl_posture.setStyleSheet("font-size: 13px; font-weight: 600; color: #ABB2BF; border: none;")
        horizontalLayout_subdata.addWidget(self.lbl_posture)

        horizontalLayout_subdata.addStretch()

        self.lbl_fall_count = QLabel("跌倒告警: 0 次", self.control_card)
        self.lbl_fall_count.setStyleSheet("font-size: 13px; font-weight: 600; color: #E06C75; border: none;")
        horizontalLayout_subdata.addWidget(self.lbl_fall_count)
        verticalLayout_control.addLayout(horizontalLayout_subdata)

        self.log_title = QLabel("系统运行日志", self.control_card)
        self.log_title.setFont(QFont("Microsoft YaHei", 11, QFont.Weight.Bold))
        self.log_title.setStyleSheet("color: #5C6370; border: none;")
        verticalLayout_control.addWidget(self.log_title)

        self.log_list = QListWidget(self.control_card)
        self.log_list.setStyleSheet("""
            QListWidget {
                background-color: #181A1F;
                border: 1px solid #282C34;
                border-radius: 6px;
                color: #98C379;
                font-size: 12px;
                padding: 4px;
            }
        """)
        verticalLayout_control.addWidget(self.log_list)

        horizontalLayout_content.addWidget(self.control_card)
        verticalLayout_right_container.addLayout(horizontalLayout_content)

        horizontalLayout_main.addWidget(self.right_container)
        MainWindow.setCentralWidget(self.centralwidget)