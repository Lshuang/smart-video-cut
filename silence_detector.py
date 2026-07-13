"""
静音检测模块
- 从视频中提取音频
- 使用 pydub 检测静音片段
- 返回需要保留的非静音段落时间点
"""

import os
import subprocess
import json
from pydub import AudioSegment
from pydub.silence import detect_nonsilent
from config import (
    FFMPEG_PATH, FFPROBE_PATH, TEMP_DIR,
    SILENCE_THRESHOLD_DB, SILENCE_MIN_DURATION_MS, KEEP_PADDING_MS
)


def get_video_duration(video_path: str) -> float:
    """获取视频时长 (秒)"""
    cmd = [
        FFPROBE_PATH, "-v", "quiet", "-print_format", "json",
        "-show_format", video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    info = json.loads(result.stdout)
    return float(info["format"]["duration"])


def get_video_info(video_path: str) -> dict:
    """获取视频信息 (宽高、帧率、编码等)"""
    cmd = [
        FFPROBE_PATH, "-v", "quiet", "-print_format", "json",
        "-show_streams", "-show_format", video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    info = json.loads(result.stdout)

    video_stream = None
    audio_stream = None
    for stream in info.get("streams", []):
        if stream["codec_type"] == "video" and video_stream is None:
            video_stream = stream
        elif stream["codec_type"] == "audio" and audio_stream is None:
            audio_stream = stream

    duration = float(info["format"]["duration"])
    width = int(video_stream["width"]) if video_stream else 1920
    height = int(video_stream["height"]) if video_stream else 1080
    fps_str = video_stream.get("r_frame_rate", "30/1") if video_stream else "30/1"

    # 解析帧率 (可能为 "30000/1001" 格式)
    if "/" in fps_str:
        num, den = fps_str.split("/")
        fps = float(num) / float(den)
    else:
        fps = float(fps_str)

    has_audio = audio_stream is not None

    return {
        "duration": duration,
        "width": width,
        "height": height,
        "fps": fps,
        "has_audio": has_audio,
        "video_codec": video_stream.get("codec_name", "h264") if video_stream else "h264",
        "audio_codec": audio_stream.get("codec_name", "aac") if audio_stream else None,
        "sample_rate": int(audio_stream.get("sample_rate", 44100)) if audio_stream else 44100,
    }


def extract_audio(video_path: str, audio_output_path: str = None) -> str:
    """从视频中提取音频为 WAV 格式"""
    if audio_output_path is None:
        audio_output_path = os.path.join(TEMP_DIR, "extracted_audio.wav")

    cmd = [
        FFMPEG_PATH, "-y", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        audio_output_path
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return audio_output_path


def detect_non_silent_segments(audio_path: str) -> list:
    """
    检测非静音段落
    返回: [(start_ms, end_ms), ...]
    """
    audio = AudioSegment.from_file(audio_path)
    min_silence_len = SILENCE_MIN_DURATION_MS

    non_silent_ranges = detect_nonsilent(
        audio,
        min_silence_len=min_silence_len,
        silence_thresh=SILENCE_THRESHOLD_DB,
        seek_step=10  # 每10ms检测一次，平衡精度和速度
    )

    # 添加 padding，避免剪太狠
    padded_ranges = []
    for start_ms, end_ms in non_silent_ranges:
        new_start = max(0, start_ms - KEEP_PADDING_MS)
        new_end = min(len(audio), end_ms + KEEP_PADDING_MS)
        padded_ranges.append((new_start, new_end))

    return padded_ranges


def merge_close_segments(segments: list, min_gap_ms: int = 500) -> list:
    """
    合并间隔很近的段落
    如果两段之间间隔小于 min_gap_ms，则合并为一段
    """
    if not segments:
        return []

    merged = [segments[0]]
    for current in segments[1:]:
        prev = merged[-1]
        gap = current[0] - prev[1]
        if gap < min_gap_ms:
            # 合并
            merged[-1] = (prev[0], current[1])
        else:
            merged.append(current)

    return merged


def filter_short_segments(segments: list, min_duration_ms: int = 1000) -> list:
    """过滤掉过短的段落（可能是噪音）"""
    return [(s, e) for s, e in segments if (e - s) >= min_duration_ms]


def detect_silence_and_get_cuts(video_path: str) -> dict:
    """
    主函数：检测视频静音并生成切割点

    返回:
    {
        "video_info": {...},
        "segments": [(start_sec, end_sec), ...],  # 保留的段落 (秒)
        "total_original_duration": float,
        "total_kept_duration": float,
        "total_removed_duration": float,
    }
    """
    print("[静音检测] 获取视频信息...")
    video_info = get_video_info(video_path)
    duration = video_info["duration"]

    if not video_info["has_audio"]:
        print("[静音检测] 视频无音轨，保留全部内容")
        return {
            "video_info": video_info,
            "segments": [(0.0, duration)],
            "total_original_duration": duration,
            "total_kept_duration": duration,
            "total_removed_duration": 0.0,
        }

    print(f"[静音检测] 视频时长: {duration:.1f}秒")

    # 提取音频
    print("[静音检测] 提取音频...")
    audio_path = extract_audio(video_path)

    # 检测非静音段落
    print(f"[静音检测] 检测静音 (阈值={SILENCE_THRESHOLD_DB}dB, 最小静音={SILENCE_MIN_DURATION_MS}ms)...")
    non_silent = detect_non_silent_segments(audio_path)
    print(f"[静音检测] 检测到 {len(non_silent)} 个非静音段落")

    # 合并太近的段落
    non_silent = merge_close_segments(non_silent, min_gap_ms=500)

    # 过滤短段落
    non_silent = filter_short_segments(non_silent, min_duration_ms=1000)

    # 转换为秒
    segments_sec = [(s / 1000.0, e / 1000.0) for s, e in non_silent]
    total_kept = sum(e - s for s, e in segments_sec)

    print(f"[静音检测] 合并过滤后: {len(segments_sec)} 个段落")
    print(f"[静音检测] 保留时长: {total_kept:.1f}秒 / 移除: {duration - total_kept:.1f}秒")

    return {
        "video_info": video_info,
        "segments": segments_sec,
        "total_original_duration": duration,
        "total_kept_duration": total_kept,
        "total_removed_duration": duration - total_kept,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        result = detect_silence_and_get_cuts(sys.argv[1])
        for i, (s, e) in enumerate(result["segments"]):
            print(f"  段落 {i+1}: {s:.2f}s - {e:.2f}s (时长 {e-s:.2f}s)")
    else:
        print("用法: python silence_detector.py <video_path>")