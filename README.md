# MediaPipe Fall

一个基于 **YOLOv8**、**MediaPipe** 与 **PyQt6** 的桌面端人员跌倒检测系统。它支持摄像头和本地视频输入，实时识别画面中的人员姿态；在检测到疑似跌倒时自动触发告警，并将事件片段保存下来供回放。

> 本项目适用于原型验证、课程设计和智能安防场景探索；检测结果不应作为医疗诊断或唯一的安全决策依据。

## 功能特性

- YOLOv8 实时定位视频画面中的人员
- MediaPipe Pose 提取人体肩部、髋部等关键点
- 根据躯干倾角识别站立、跌倒中与平躺姿态
- 支持默认摄像头与 `.mp4`、`.avi`、`.mov` 本地视频
- 跌倒告警时自动保存视频片段至 `result/`
- 提供告警次数、实时状态、运行日志及历史片段回放界面

## 技术原理

1. 使用 YOLOv8 检测每帧中的人员（COCO 类别 `person`）。
2. 对人员区域进行 MediaPipe 姿态估计。
3. 以左右肩膀与左右髋部的中点计算躯干倾角。
4. 根据阈值判断姿态：小于 20° 为站立，大于 50° 为平躺，介于两者之间视为跌倒中。
5. 当跌倒状态连续出现约 0.1–0.5 秒时触发告警，并写入事件视频；姿态恢复后结束录制。

## 环境要求

- Windows 10/11（已在 Windows 环境开发）
- Python 3.8–3.11
- 摄像头（使用实时检测时需要）

## 快速开始

```bash
git clone https://github.com/<your-username>/Mediapipe-Fall-Detector.git
cd Mediapipe-Fall-Detector

python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

将 YOLOv8 Nano 权重文件放在项目根目录，并命名为 `yolov8n.pt`。然后运行：

```bash
python main.py
```

首次使用也可以从 [Ultralytics YOLOv8](https://github.com/ultralytics/ultralytics) 获取 `yolov8n.pt`。若网络可用，Ultralytics 通常会在权重缺失时尝试自动下载。

## 使用说明

1. 启动程序后，选择“切换为摄像头”或“导入视频文件”。
2. 点击“启动实时检测”。
3. 在右侧查看当前姿态、告警状态、告警次数和运行日志。
4. 检测到跌倒后，告警片段会保存到 `result/`。
5. 点击“历史跌倒片段”可在程序内查看已保存的视频。

## 项目结构

```text
Mediapipe-Fall-Detector/
├── main.py              # 检测流程、告警逻辑与应用入口
├── diedao.py            # PyQt6 界面代码
├── diedao.ui            # Qt Designer 界面文件
├── yolov8n.pt           # YOLOv8 权重（需自行准备）
├── video/               # 示例/测试视频（建议不提交大文件）
├── result/              # 自动生成的告警片段
├── requirements.txt     # Python 依赖
└── PROJECT_OVERVIEW.md  # 项目概述
```

## 注意事项

- 本项目默认使用摄像头索引 `0`；如有多个摄像头，可在 `main.py` 中调整。
- 程序在 Windows 下会优先使用 `msyh.ttc` 或 `simhei.ttf` 绘制中文；若中文显示异常，请安装相应字体或修改字体路径。
- 姿态阈值、连续帧判定时长会影响灵敏度和误报率，建议针对实际安装高度、拍摄角度和场景进行调参。
- 建议不要将 `result/`、大体积测试视频或模型权重提交到 Git 仓库；可通过 Releases、网盘或模型仓库分发它们。
