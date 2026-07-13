"""
字幕叠加模块
- 为每个视频段落叠加主题文字
- 支持基本动画效果
- 剪映风格的文字样式
"""

import os
import subprocess
from config import (
    FFMPEG_PATH, TEMP_DIR, OUTPUT_DIR,
    PROGRESS_BAR_FONT_FILE, OUTPUT_FPS,
)


def add_segment_text(
    input_path: str,
    text: str,
    output_path: str = None,
    duration: float = None,
    position: str = "bottom-center",
    font_size: int = 32,
    font_color: str = "white",
    animation: str = "fade",
) -> str:
    """
    给视频片段添加主题文字

    参数:
        input_path: 输入视频
        text: 文字内容
        output_path: 输出路径
        duration: 视频时长
        position: 位置 (bottom-center, top-center, center)
        font_size: 字号
        font_color: 文字颜色
        animation: 动画效果 (fade, none)

    返回: 输出视频路径
    """
    if output_path is None:
        base = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(TEMP_DIR, f"{base}_titled.mp4")

    # 获取视频时长
    if duration is None:
        from silence_detector import get_video_duration
        duration = get_video_duration(input_path)

    # Windows 字体路径 (FFmpeg drawtext 格式)
    font_file = "C\\:/Windows/Fonts/msyh.ttc"

    # 根据位置计算坐标
    if position == "bottom-center":
        x_expr = "(w-text_w)/2"
        y_expr = "h-text_h-60"
    elif position == "top-center":
        x_expr = "(w-text_w)/2"
        y_expr = "80"
    else:
        x_expr = "(w-text_w)/2"
        y_expr = "(h-text_h)/2"

    # 阴影 + 主体文字 (无动画，保持简洁)
    shadow_filter = (
        f"drawtext=fontfile='{font_file}':"
        f"text='{text}':fontcolor=black@0.5:fontsize={font_size}:"
        f"x={x_expr}+2:y={y_expr}+2"
    )
    main_filter = (
        f"drawtext=fontfile='{font_file}':"
        f"text='{text}':fontcolor={font_color}:fontsize={font_size}:"
        f"x={x_expr}:y={y_expr}"
    )

    vf_chain = f"{shadow_filter},{main_filter}"

    cmd = [
        FFMPEG_PATH, "-y",
        "-i", input_path,
        "-vf", vf_chain,
        "-c:v", "libx264",
        "-c:a", "copy",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "18",
        output_path
    ]

    subprocess.run(cmd, capture_output=True, check=True, text=True)
    return output_path


def add_segment_topics_batch(
    segment_paths: list,
    topics: list,
    segment_durations: list = None
) -> list:
    """批量给视频段落添加主题文字"""
    result_paths = []

    for i, (seg_path, topic) in enumerate(zip(segment_paths, topics)):
        duration = segment_durations[i] if segment_durations else None
        output = os.path.join(TEMP_DIR, f"segment_{i:03d}_titled.mp4")

        print(f"  [字幕] 段落 {i+1}: {topic}")

        result = add_segment_text(
            seg_path,
            topic,
            output,
            duration=duration,
            position="bottom-center",
            font_size=30,
            animation="fade",
        )
        result_paths.append(result)

    return result_paths


def build_subtitle_overlay_command(
    video_path: str,
    subtitles: list,
    output_path: str
) -> str:
    """使用 SRT 字幕叠加"""
    srt_path = os.path.join(TEMP_DIR, "subtitles.srt")
    with open(srt_path, "w", encoding="utf-8") as f:
        for i, sub in enumerate(subtitles):
            start = _format_srt_time(sub["start"])
            end = _format_srt_time(sub["end"])
            f.write(f"{i+1}\n")
            f.write(f"{start} --> {end}\n")
            f.write(f"{sub['text']}\n\n")

    escaped_srt = srt_path.replace("\\", "/").replace(":", "\\:")
    vf = f"subtitles='{escaped_srt}':force_style='FontSize=32,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Outline=1,Shadow=1,Alignment=2,MarginV=60'"

    cmd = [
        FFMPEG_PATH, "-y",
        "-i", video_path,
        "-vf", vf,
        "-c:v", "libx264",
        "-c:a", "copy",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "18",
        output_path
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def _format_srt_time(seconds: float) -> str:
    """格式化 SRT 时间戳"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 2:
        add_segment_text(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    else:
        print("用法: python text_overlay.py <video> <text> [output]")