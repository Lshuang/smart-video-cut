"""
音频特效模块
- 生成转场音效 (whoosh, sweep)
- 生成章节提示音
- 用于增强章节过渡的听觉体验
"""

import os
import struct
import math
import wave
import subprocess
from config import FFMPEG_PATH, TEMP_DIR, TRANSITION_DURATION_SEC


def _write_wav(output_path: str, samples: list, sample_rate: int = 44100):
    """将样本写入 WAV 文件"""
    with wave.open(output_path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack('<' + 'h' * len(samples), *samples))
    return output_path


def generate_sine_wave(
    frequency: float,
    duration: float,
    sample_rate: int = 44100,
    amplitude: float = 0.3,
    fade_in: float = 0.05,
    fade_out: float = 0.1
) -> bytes:
    """生成正弦波音频数据"""
    num_samples = int(duration * sample_rate)
    samples = []

    for i in range(num_samples):
        t = i / sample_rate
        # 频率扫描 (低到高，产生 whoosh 效果)
        freq = frequency * (1.0 + t / duration * 2.0)

        # 正弦波
        value = math.sin(2 * math.pi * freq * t)

        # 淡入淡出
        if i < fade_in * sample_rate:
            value *= i / (fade_in * sample_rate)
        if i > (duration - fade_out) * sample_rate:
            value *= (num_samples - i) / (fade_out * sample_rate)

        samples.append(int(value * amplitude * 32767))

    # 打包为 16-bit PCM
    return struct.pack('<' + 'h' * len(samples), *samples)


def generate_whoosh_sound(output_path: str = None) -> str:
    """
    生成 whoosh 转场音效
    从低频到高频的快速扫描，模拟"嗖"的转场音
    """
    if output_path is None:
        output_path = os.path.join(TEMP_DIR, "whoosh.wav")

    duration = 0.4  # 短促的转场音
    sample_rate = 44100
    num_samples = int(duration * sample_rate)
    samples = []

    for i in range(num_samples):
        t = i / sample_rate
        # 频率从 200Hz 扫描到 2000Hz
        freq = 200 + 1800 * (t / duration) ** 1.5

        # 加入少量噪声使其更自然
        noise = (hash(str(i)) % 1000 - 500) / 500.0 * 0.05

        value = math.sin(2 * math.pi * freq * t) + noise

        # 包络 (快速起音，稍慢衰减)
        attack = min(1.0, t / 0.02)  # 20ms 起音
        release = max(0.0, 1.0 - (t - duration * 0.6) / (duration * 0.4))  # 衰减
        envelope = attack * release

        value *= envelope * 0.4
        samples.append(int(value * 32767))

    _write_wav(output_path, samples, sample_rate)
    return output_path


def generate_chapter_ding(output_path: str = None) -> str:
    """
    生成章节提示音
    清脆的"叮"一声，提示新章节开始
    """
    if output_path is None:
        output_path = os.path.join(TEMP_DIR, "chapter_ding.wav")

    duration = 0.3
    sample_rate = 44100
    num_samples = int(duration * sample_rate)
    samples = []

    for i in range(num_samples):
        t = i / sample_rate
        # 高频音 + 谐波
        value = (
            math.sin(2 * math.pi * 1200 * t) * 0.5 +
            math.sin(2 * math.pi * 2400 * t) * 0.3 +
            math.sin(2 * math.pi * 3600 * t) * 0.15
        )
        # 快速衰减
        envelope = math.exp(-t * 8)
        value *= envelope * 0.5
        samples.append(int(value * 32767))

    _write_wav(output_path, samples, sample_rate)
    return output_path


def generate_transition_audio(duration: float = None, output_path: str = None) -> str:
    """
    生成完整的转场音频 (whoosh + 叮)

    返回 WAV 文件路径
    """
    if duration is None:
        duration = TRANSITION_DURATION_SEC
    if output_path is None:
        output_path = os.path.join(TEMP_DIR, "transition_audio.wav")

    sample_rate = 44100
    num_samples = int(duration * sample_rate)
    samples = []

    for i in range(num_samples):
        t = i / sample_rate
        value = 0.0

        # Whoosh 效果 (前 0.5 秒)
        if t < 0.5:
            freq = 150 + 2500 * (t / 0.5) ** 2
            value += math.sin(2 * math.pi * freq * t) * 0.2
            # 噪声质感
            noise = (hash(str(i * 3)) % 1000 - 500) / 500.0 * 0.03
            value += noise

        # 叮声 (0.3 秒处)
        if 0.3 <= t < 0.6:
            ding_t = t - 0.3
            ding = (
                math.sin(2 * math.pi * 1500 * ding_t) * 0.4 +
                math.sin(2 * math.pi * 3000 * ding_t) * 0.2
            )
            ding *= math.exp(-ding_t * 10)
            value += ding

        # 淡入淡出
        if t < 0.05:
            value *= t / 0.05
        if t > duration - 0.1:
            value *= (duration - t) / 0.1

        samples.append(int(value * 32767))

    _write_wav(output_path, samples, sample_rate)
    return output_path


def wav_to_aac(wav_path: str, aac_path: str = None) -> str:
    """将 WAV 转换为 AAC (用于视频)"""
    if aac_path is None:
        aac_path = wav_path.replace(".wav", ".aac")

    cmd = [
        FFMPEG_PATH, "-y",
        "-i", wav_path,
        "-c:a", "aac",
        "-b:a", "128k",
        aac_path
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return aac_path


def generate_silence_audio(duration: float, output_path: str = None) -> str:
    """生成静音音频 (用于填充)"""
    if output_path is None:
        output_path = os.path.join(TEMP_DIR, "silence.wav")

    cmd = [
        FFMPEG_PATH, "-y",
        "-f", "lavfi",
        "-i", f"anullsrc=r=44100:cl=stereo:d={duration}",
        "-c:a", "pcm_s16le",
        output_path
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return output_path


def generate_segment_topic_audio(text: str, output_path: str = None) -> str:
    """
    生成段落的主题提示音
    短促的提示音表示新段落开始
    """
    if output_path is None:
        output_path = os.path.join(TEMP_DIR, "topic_ding.wav")

    duration = 0.25
    sample_rate = 44100
    num_samples = int(duration * sample_rate)
    samples = []

    for i in range(num_samples):
        t = i / sample_rate
        # 上升音
        freq = 800 + 400 * t / duration
        value = math.sin(2 * math.pi * freq * t)
        envelope = math.exp(-t * 6) * 0.4
        value *= envelope
        samples.append(int(value * 32767))

    _write_wav(output_path, samples, sample_rate)
    return output_path


if __name__ == "__main__":
    whoosh = generate_whoosh_sound()
    print(f"Whoosh: {whoosh}")
    ding = generate_chapter_ding()
    print(f"Ding: {ding}")
    transition = generate_transition_audio()
    print(f"Transition: {transition}")