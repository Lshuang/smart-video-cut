"""
测试脚本 - 生成测试视频并运行完整的智能剪口播流程
用于验证所有功能模块
"""

import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import FFMPEG_PATH, TEMP_DIR, OUTPUT_DIR


def create_test_video(output_path: str = None) -> str:
    """
    生成测试视频:
    - 30秒，1280x720
    - 模拟口播：正弦波音频模拟人声 + 静音间隔
    """
    if output_path is None:
        output_path = os.path.join(TEMP_DIR, "test_video.mp4")

    os.makedirs(TEMP_DIR, exist_ok=True)

    print("=" * 55)
    print("  生成测试视频")
    print("=" * 55)
    print("  结构: 有声(2s) -> 静音(1.5s) -> 有声(3s) -> 静音(2s)")
    print("       -> 有声(5s) -> 静音(1s) -> 有声(3s) -> 静音(1.5s)")
    print("       -> 有声(4s) -> 静音(2s) -> 有声(5s)")

    # 用 Python 生成带音频的测试视频
    # 方法: 生成一个纯色视频帧 + 生成带静音间隔的音频，然后合并

    import numpy as np
    from PIL import Image

    # 1. 生成30秒的纯色视频 (用 FFmpeg color 源)
    color_video = os.path.join(TEMP_DIR, "test_bg.mp4")
    cmd_color = [
        FFMPEG_PATH, "-y",
        "-f", "lavfi",
        "-i", "color=c=0x1a1a2e:s=1280x720:r=30:d=30",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "ultrafast",
        "-crf", "18",
        color_video
    ]
    subprocess.run(cmd_color, capture_output=True, check=True)
    print("  ✅ 背景视频生成")

    # 2. 生成带静音间隔的音频
    audio_path = os.path.join(TEMP_DIR, "test_audio.wav")
    generate_test_audio(audio_path)
    print("  ✅ 测试音频生成")

    # 3. 合并视频和音频
    cmd_merge = [
        FFMPEG_PATH, "-y",
        "-i", color_video,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        output_path
    ]
    subprocess.run(cmd_merge, capture_output=True, check=True)
    print(f"  ✅ 测试视频已生成: {output_path}")
    print(f"  时长: 30秒, 分辨率: 1280x720")
    return output_path


def generate_test_audio(output_path: str):
    """生成带静音间隔的测试音频 (模拟口播)"""
    import wave
    import struct
    import math

    sample_rate = 44100
    total_duration = 30
    num_samples = total_duration * sample_rate

    speech_segments = [
        (0, 2),
        (3.5, 6.5),
        (8.5, 13.5),
        (14.5, 17.5),
        (19, 23),
        (25, 30),
    ]

    samples = []
    for i in range(num_samples):
        t = i / sample_rate
        value = 0.0
        is_speech = any(start <= t < end for start, end in speech_segments)
        if is_speech:
            freq = 220 + 50 * math.sin(2 * math.pi * 0.3 * t)
            value = (
                math.sin(2 * math.pi * freq * t) * 0.4 +
                math.sin(2 * math.pi * freq * 2 * t) * 0.2
            )
            noise_val = (hash(str(i * 7)) % 1000 - 500) / 500.0 * 0.05
            value += noise_val
            value *= 0.6
            for seg_start, seg_end in speech_segments:
                if seg_start <= t < seg_end:
                    if t < seg_start + 0.1:
                        value *= (t - seg_start) / 0.1
                    if t > seg_end - 0.1:
                        value *= (seg_end - t) / 0.1
                    break
        samples.append(int(max(-32767, min(32767, value * 32767))))

    with wave.open(output_path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack('<' + 'h' * len(samples), *samples))


def run_full_test(video_path: str):
    """运行完整测试流程"""
    print("\n" + "=" * 55)
    print("  启动智能剪口播测试")
    print("=" * 55)

    from video_editor import process_video

    output = process_video(
        input_path=video_path,
        skip_speech=True,
        segment_titles=[
            "开场介绍",
            "底层技术原理",
            "详细操作步骤",
            "进阶技巧分享",
            "实用建议",
            "总结与回顾"
        ],
    )

    print(f"\n测试完成! 输出: {output}")
    return output


if __name__ == "__main__":
    print("╔══════════════════════════════════════════════╗")
    print("║     智能剪口播 - 端到端测试                 ║")
    print("╚══════════════════════════════════════════════╝")

    test_video = create_test_video()
    if not test_video:
        print("无法生成测试视频，退出")
        sys.exit(1)

    t_start = time.time()
    try:
        run_full_test(test_video)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    t_elapsed = time.time() - t_start
    print(f"\n总耗时: {t_elapsed:.1f} 秒")