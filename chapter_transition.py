"""
章节过渡转场页生成模块
- 生成 YouTube 风格的章节过渡动画
- 显示章节编号、标题、时长
- 现代简洁的设计风格
"""

import os
import subprocess
import math
from config import (
    FFMPEG_PATH, TEMP_DIR, OUTPUT_DIR,
    TRANSITION_DURATION_SEC, TRANSITION_BG_COLOR,
    TRANSITION_ACCENT_COLOR, TRANSITION_TEXT_COLOR,
    TRANSITION_FONT_SIZE_TITLE, TRANSITION_FONT_SIZE_CHAPTER,
    PROGRESS_BAR_FONT_FILE, OUTPUT_FPS
)


def hex_to_rgb(hex_color: str) -> tuple:
    """将 hex 颜色转换为 RGB 元组"""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def generate_transition_video(
    chapter: dict,
    chapter_index: int,
    total_chapters: int,
    video_width: int,
    video_height: int,
    output_path: str = None
) -> str:
    """
    生成单个章节的过渡转场视频

    设计: YouTube 风格
    - 深色背景 + 左侧彩色竖条
    - 章节编号 (大号)
    - 章节标题 (中等)
    - 时长信息
    - 淡入淡出动画

    参数:
        chapter: {"start": float, "end": float, "title": str, "summary": str}
        chapter_index: 章节序号 (从1开始)
        total_chapters: 总章节数
        video_width: 视频宽度
        video_height: 视频高度
        output_path: 输出路径
    """
    if output_path is None:
        output_path = os.path.join(TEMP_DIR, f"transition_ch{chapter_index:02d}.mp4")

    duration = TRANSITION_DURATION_SEC
    total_frames = int(duration * OUTPUT_FPS)

    from PIL import Image, ImageDraw, ImageFont

    try:
        font_title = ImageFont.truetype(PROGRESS_BAR_FONT_FILE, TRANSITION_FONT_SIZE_TITLE)
        font_chapter = ImageFont.truetype(PROGRESS_BAR_FONT_FILE, TRANSITION_FONT_SIZE_CHAPTER)
        font_small = ImageFont.truetype(PROGRESS_BAR_FONT_FILE, 20)
    except Exception:
        font_title = ImageFont.load_default()
        font_chapter = ImageFont.load_default()
        font_small = ImageFont.load_default()

    bg_rgb = hex_to_rgb(TRANSITION_BG_COLOR)
    accent_rgb = hex_to_rgb(TRANSITION_ACCENT_COLOR)

    chapter_duration = chapter["end"] - chapter["start"]
    title = chapter["title"]

    # 如果标题太长，换行
    if len(title) > 25:
        # 尝试在中间位置换行
        mid = len(title) // 2
        # 找到最近的空格
        space_idx = title.rfind(" ", 0, mid + 10)
        if space_idx == -1:
            space_idx = title.find(" ", mid - 5)
        if space_idx != -1:
            title = title[:space_idx] + "\n" + title[space_idx+1:]

    print(f"[转场] 生成章节 {chapter_index} 转场: {chapter['title']}")

    frames_dir = os.path.join(TEMP_DIR, f"transition_frames_ch{chapter_index:02d}")
    os.makedirs(frames_dir, exist_ok=True)

    for frame_idx in range(total_frames):
        progress = frame_idx / total_frames
        img = Image.new("RGB", (video_width, video_height), bg_rgb)
        draw = ImageDraw.Draw(img)

        # === 动画计算 ===
        # 淡入效果 (前20% 和后20% 是淡入淡出)
        fade_in = min(1.0, progress / 0.2)
        fade_out = min(1.0, (1.0 - progress) / 0.2)
        opacity = fade_in * fade_out

        # 左侧彩色竖条动画 (从左侧滑入)
        accent_bar_width = 8
        bar_x = int(-accent_bar_width + (20 + accent_bar_width) * min(1.0, progress / 0.3))
        accent_color = tuple(int(c * opacity) for c in accent_rgb)
        draw.rectangle(
            [(bar_x, 0), (bar_x + accent_bar_width, video_height)],
            fill=accent_color
        )

        # 章节编号 (从上方滑入)
        num_text = f"PART {chapter_index:02d}"
        num_alpha = int(255 * opacity)
        num_y_offset = int(50 * (1 - min(1.0, progress / 0.3)))  # 滑入动画
        num_y = video_height // 2 - 120 + num_y_offset

        # 编号文字阴影
        draw.text(
            (video_width // 2 + 2, num_y + 2),
            num_text,
            font=font_chapter,
            fill=(0, 0, 0),
            anchor="mt"
        )
        draw.text(
            (video_width // 2, num_y),
            num_text,
            font=font_chapter,
            fill=(*accent_rgb,),
            anchor="mt"
        )

        # 章节标题 (从下方滑入)
        title_lines = title.split("\n")
        title_y_base = video_height // 2 - 20
        title_y_offset = int(30 * (1 - min(1.0, progress / 0.4)))

        for li, line in enumerate(title_lines):
            line_y = title_y_base + li * (TRANSITION_FONT_SIZE_TITLE + 10) + title_y_offset
            # 阴影
            draw.text(
                (video_width // 2 + 2, line_y + 2),
                line,
                font=font_title,
                fill=(0, 0, 0),
                anchor="mt"
            )
            # 主体
            draw.text(
                (video_width // 2, line_y),
                line,
                font=font_title,
                fill=(255, 255, 255),
                anchor="mt"
            )

        # 时长信息
        mins = int(chapter_duration // 60)
        secs = int(chapter_duration % 60)
        duration_text = f"时长 {mins}:{secs:02d}"
        dur_y = video_height // 2 + 100
        draw.text(
            (video_width // 2 + 1, dur_y + 1),
            duration_text,
            font=font_small,
            fill=(0, 0, 0),
            anchor="mt"
        )
        draw.text(
            (video_width // 2, dur_y),
            duration_text,
            font=font_small,
            fill=(180, 180, 190),
            anchor="mt"
        )

        # 底部进度指示器
        dot_count = total_chapters
        dot_spacing = 20
        dot_total_width = (dot_count - 1) * dot_spacing
        dot_start_x = video_width // 2 - dot_total_width // 2
        dot_y = video_height - 60

        for d in range(dot_count):
            dx = dot_start_x + d * dot_spacing
            if d == chapter_index - 1:
                # 当前章节 - 高亮
                dot_r = 6
                draw.ellipse(
                    [(dx - dot_r, dot_y - dot_r), (dx + dot_r, dot_y + dot_r)],
                    fill=accent_rgb
                )
            else:
                dot_r = 3
                draw.ellipse(
                    [(dx - dot_r, dot_y - dot_r), (dx + dot_r, dot_y + dot_r)],
                    fill=(80, 80, 90)
                )

        # 保存帧
        frame_path = os.path.join(frames_dir, f"frame_{frame_idx:06d}.png")
        img.save(frame_path)

    # 编码为视频
    print(f"[转场] 编码章节 {chapter_index} 转场视频...")
    cmd = [
        FFMPEG_PATH, "-y",
        "-framerate", str(OUTPUT_FPS),
        "-i", os.path.join(frames_dir, "frame_%06d.png"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", "18",
        output_path
    ]
    subprocess.run(cmd, capture_output=True, check=True)

    print(f"[转场] 转场视频已生成: {output_path}")
    return output_path


def generate_all_transitions(
    chapters: list,
    video_width: int,
    video_height: int
) -> list:
    """
    为所有章节生成过渡转场视频

    返回: [transition_video_path, ...]
    """
    transitions = []
    total = len(chapters)

    for i, chapter in enumerate(chapters):
        output_path = os.path.join(TEMP_DIR, f"transition_ch{i+1:02d}.mp4")
        path = generate_transition_video(
            chapter, i + 1, total,
            video_width, video_height,
            output_path
        )
        transitions.append(path)

    return transitions


if __name__ == "__main__":
    test_chapter = {
        "start": 0,
        "end": 60,
        "title": "开场介绍与工具概述",
        "summary": "介绍今天要讲的内容"
    }
    generate_transition_video(test_chapter, 1, 3, 1920, 1080)