"""
进度条生成模块
- 生成可视化的进度条视频 (显示在视频上方)
- 进度条上显示各章节主题标签
- 进度条随时间推移填充颜色
"""

import os
import subprocess
from config import (
    FFMPEG_PATH, TEMP_DIR, OUTPUT_DIR,
    PROGRESS_BAR_HEIGHT, PROGRESS_BAR_BG_COLOR,
    PROGRESS_BAR_FILL_COLOR, PROGRESS_BAR_FONT_COLOR,
    PROGRESS_BAR_FONT_SIZE, PROGRESS_BAR_FONT_FILE,
    OUTPUT_FPS
)


def generate_progress_bar_video(
    chapters: list,
    total_duration: float,
    video_width: int,
    output_path: str = None
) -> str:
    """
    生成进度条视频

    进度条显示在视频上方，包含:
    - 半透明背景条
    - 各章节的标签文字
    - 随时间填充的进度色块

    参数:
        chapters: 章节列表 [{"start": float, "end": float, "title": str}, ...]
        total_duration: 总时长 (秒)
        video_width: 视频宽度 (像素)
        output_path: 输出路径
    """
    if output_path is None:
        output_path = os.path.join(TEMP_DIR, "progress_bar.mp4")

    bar_height = PROGRESS_BAR_HEIGHT
    bar_y = 0
    font_file = PROGRESS_BAR_FONT_FILE
    font_size = PROGRESS_BAR_FONT_SIZE

    # 构建 FFmpeg drawtext 滤镜链
    # 策略: 使用 color 源生成背景，然后叠加文字和进度填充

    # 计算章节在进度条上的位置
    chapter_labels = []
    for i, ch in enumerate(chapters):
        # 章节在总时长中的位置比例
        start_ratio = ch["start"] / total_duration if total_duration > 0 else 0
        end_ratio = ch["end"] / total_duration if total_duration > 0 else 1
        center_ratio = (start_ratio + end_ratio) / 2
        x_pos = int(video_width * center_ratio)

        # 章节宽度
        chapter_width = int(video_width * (end_ratio - start_ratio))

        # 截断长标题
        title = ch["title"]
        if len(title) > 15:
            title = title[:14] + "…"

        chapter_labels.append({
            "x": x_pos,
            "width": max(chapter_width, 80),
            "title": title,
            "start": ch["start"],
            "end": ch["end"],
        })

    # 构建复杂的 FFmpeg 滤镜图
    # 1. 背景色条
    # 2. 进度填充 (随时间变化的矩形)
    # 3. 章节分隔线
    # 4. 章节标签文字

    filter_parts = []

    # 背景色条
    bg_color = PROGRESS_BAR_BG_COLOR.replace("0x", "").replace("@", "@")
    bg_filter = (
        f"color=size={video_width}x{bar_height}:color={bg_color}:rate={OUTPUT_FPS}:duration={total_duration}"
    )
    filter_parts.append(f"[0:v]null[bg]")

    # 实际构建时使用更简单的方法 - 用 Python 生成帧，然后用 FFmpeg 编码
    # 因为 FFmpeg 的 drawtext 在处理复杂进度条时比较困难

    # 使用 Python 生成带进度条的帧序列
    print(f"[进度条] 生成进度条帧...")
    frames_dir = os.path.join(TEMP_DIR, "progress_frames")
    os.makedirs(frames_dir, exist_ok=True)

    from PIL import Image, ImageDraw, ImageFont
    import numpy as np

    try:
        font = ImageFont.truetype(font_file, font_size)
        font_small = ImageFont.truetype(font_file, font_size - 4)
    except Exception:
        font = ImageFont.load_default()
        font_small = ImageFont.load_default()

    total_frames = int(total_duration * OUTPUT_FPS)

    for frame_idx in range(total_frames):
        current_time = frame_idx / OUTPUT_FPS
        progress_ratio = current_time / total_duration if total_duration > 0 else 0

        # 创建帧图像 (RGBA, 半透明)
        img = Image.new("RGBA", (video_width, bar_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # 背景条 (半透明深色)
        bg_rgba = (20, 20, 30, 140)
        draw.rectangle([(0, 0), (video_width, bar_height)], fill=bg_rgba)

        # 进度填充
        progress_width = int(video_width * progress_ratio)
        if progress_width > 0:
            fill_rgba = (233, 69, 96, 200)  # 红色
            draw.rectangle([(0, 0), (progress_width, bar_height)], fill=fill_rgba)

        # 章节分隔线和标签
        for label in chapter_labels:
            # 分隔线位置
            sep_x = int(video_width * (label["start"] / total_duration)) if total_duration > 0 else 0

            # 当前章节高亮
            is_current = label["start"] <= current_time < label["end"]
            text_color = (255, 255, 255, 255) if is_current else (200, 200, 200, 180)

            # 章节标签
            text_x = sep_x + 8
            text_y = 8
            # 确保文字不超出边界
            if text_x + 200 > video_width:
                text_x = video_width - 210

            # 文字阴影
            draw.text((text_x + 1, text_y + 1), label["title"], font=font_small, fill=(0, 0, 0, 150))
            # 文字主体
            draw.text((text_x, text_y), label["title"], font=font_small, fill=text_color)

            # 分隔线
            if sep_x > 0:
                draw.line([(sep_x, 0), (sep_x, bar_height)], fill=(255, 255, 255, 60), width=1)

        # 保存帧
        frame_path = os.path.join(frames_dir, f"frame_{frame_idx:06d}.png")
        img.save(frame_path)

        if frame_idx % 100 == 0:
            print(f"  进度: {frame_idx}/{total_frames} 帧", end="\r")

    print(f"\n[进度条] 帧生成完成: {total_frames} 帧")

    # 用 FFmpeg 将帧序列编码为视频
    print(f"[进度条] 编码进度条视频...")
    cmd = [
        FFMPEG_PATH, "-y",
        "-framerate", str(OUTPUT_FPS),
        "-i", os.path.join(frames_dir, "frame_%06d.png"),
        "-c:v", "libx264",
        "-pix_fmt", "yuva420p",  # 保留 alpha 通道
        "-preset", "fast",
        "-crf", "15",
        output_path
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    print(f"[进度条] 进度条视频已生成: {output_path}")
    return output_path


def generate_progress_bar_overlay_cmd(
    progress_bar_path: str,
    video_width: int,
    video_height: int
) -> str:
    """
    生成用于叠加进度条的 FFmpeg 滤镜参数
    进度条显示在视频上方

    返回 FFmpeg 滤镜字符串，用于 overlay
    """
    # 进度条放在视频顶部
    overlay_y = 0
    return f"[1:v]format=rgba[bar];[0:v][bar]overlay=0:{overlay_y}:shortest=1"


if __name__ == "__main__":
    # 测试
    test_chapters = [
        {"start": 0, "end": 60, "title": "开场介绍"},
        {"start": 60, "end": 180, "title": "核心功能演示"},
        {"start": 180, "end": 300, "title": "总结与建议"},
    ]
    generate_progress_bar_video(test_chapters, 300, 1920)