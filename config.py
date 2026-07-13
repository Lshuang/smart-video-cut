"""
YouTube口播视频剪辑工具 - 全局配置
"""

import os

# === 路径配置 ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
TEMP_DIR = os.path.join(BASE_DIR, "temp")

# === FFmpeg 路径 ===
FFMPEG_PATH = r"D:\ffmpeg-8.1.1-essentials_build\bin\ffmpeg.exe"
FFPROBE_PATH = r"D:\ffmpeg-8.1.1-essentials_build\bin\ffprobe.exe"

# === 静音检测配置 ===
SILENCE_THRESHOLD_DB = -35        # 静音阈值 (dB)，低于此值视为静音
SILENCE_MIN_DURATION_MS = 800     # 最短静音时长 (ms)，超过此值才剪掉
KEEP_PADDING_MS = 150             # 保留的边距，避免剪太狠 (ms)

# === 语音识别配置 ===
WHISPER_MODEL = "medium"          # tiny/base/small/medium/large-v3
WHISPER_LANGUAGE = "zh"           # 语言代码，auto=自动检测
WHISPER_DEVICE = "cpu"            # cpu/cuda

# === 章节分割配置 ===
MIN_CHAPTER_DURATION_SEC = 15     # 最短章节时长 (秒)
MAX_CHAPTER_DURATION_SEC = 180    # 最长章节时长 (秒)

# === 进度条配置 ===
PROGRESS_BAR_HEIGHT = 60          # 进度条高度 (像素)
PROGRESS_BAR_BG_COLOR = "0x000000@0.55"   # 背景色 (半透明黑)
PROGRESS_BAR_FILL_COLOR = "0xFF0000@0.85"  # 进度填充色 (红色)
PROGRESS_BAR_FONT_COLOR = "white"          # 文字颜色
PROGRESS_BAR_FONT_SIZE = 22                # 文字大小
PROGRESS_BAR_FONT_FILE = "C:/Windows/Fonts/msyh.ttc"  # 微软雅黑

# === 章节过渡转场配置 ===
TRANSITION_DURATION_SEC = 2.5     # 转场时长 (秒)
TRANSITION_BG_COLOR = "#1a1a2e"   # 转场背景色 (深蓝黑)
TRANSITION_ACCENT_COLOR = "#e94560"  # 强调色 (红色)
TRANSITION_TEXT_COLOR = "#ffffff"    # 文字颜色
TRANSITION_FONT_SIZE_TITLE = 48      # 标题字号
TRANSITION_FONT_SIZE_CHAPTER = 28    # 章节号字号

# === 视频输出配置 ===
OUTPUT_FPS = 30                   # 输出帧率
OUTPUT_CODEC = "libx264"          # 视频编码器
OUTPUT_CRF = 20                   # 视频质量 (越小越好, 18-28)
OUTPUT_PRESET = "medium"          # 编码速度预设