"""
语音转文字与主题分段模块
- 使用 faster-whisper 进行语音识别
- 基于语义分析将文本分段为主题章节
- 生成章节标题和时间戳
"""

import os
import re
from config import (
    TEMP_DIR, WHISPER_MODEL, WHISPER_LANGUAGE, WHISPER_DEVICE,
    MIN_CHAPTER_DURATION_SEC, MAX_CHAPTER_DURATION_SEC
)


def transcribe_audio(audio_path: str) -> list:
    """
    使用 faster-whisper 转录音频
    返回: [{"start": float, "end": float, "text": str}, ...]
    """
    from faster_whisper import WhisperModel

    print(f"[语音识别] 加载模型 {WHISPER_MODEL}...")
    model = WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type="int8")

    print(f"[语音识别] 开始转录...")
    segments, info = model.transcribe(
        audio_path,
        language=WHISPER_LANGUAGE if WHISPER_LANGUAGE != "auto" else None,
        beam_size=5,
        vad_filter=True,  # 使用 VAD 过滤静音
        vad_parameters=dict(
            min_silence_duration_ms=500,
        ),
    )

    results = []
    for segment in segments:
        results.append({
            "start": segment.start,
            "end": segment.end,
            "text": segment.text.strip()
        })

    print(f"[语音识别] 转录完成，共 {len(results)} 个片段")
    if info:
        print(f"[语音识别] 检测语言: {info.language} (概率: {info.language_probability:.2f})")

    return results


def segment_to_chapters(transcript_segments: list, video_duration: float) -> list:
    """
    将转录文本分段为章节

    策略:
    1. 基于时长自然分段 (每段不超过 MAX_CHAPTER_DURATION_SEC)
    2. 检测过渡词作为分界点 ("接下来", "然后", "首先", "最后" 等)
    3. 每段生成标题 (取该段最核心的一句话或关键词)

    返回: [{"start": float, "end": float, "title": str, "summary": str}, ...]
    """
    if not transcript_segments:
        return [{"start": 0, "end": video_duration, "title": "完整视频", "summary": ""}]

    # 过渡词列表
    transition_keywords = [
        "接下来", "然后", "首先", "最后", "总结", "另外",
        "下一个", "开始", "介绍", "结论", "回顾",
        "第一", "第二", "第三", "第一步", "第二步",
        "now", "next", "first", "finally", "let's",
        "所以", "那么", "好", "好的", "我们来看",
    ]

    # 初次分段：按过渡词+时长分段
    chapters = []
    current_start = transcript_segments[0]["start"]
    current_texts = []
    current_end = current_start

    for seg in transcript_segments:
        text = seg["text"]
        current_texts.append(text)
        current_end = seg["end"]

        duration = current_end - current_start
        has_transition = any(kw in text for kw in transition_keywords)

        # 分段条件：遇到过渡词且时长够了，或超过最大时长
        if duration >= MIN_CHAPTER_DURATION_SEC and (
            has_transition or duration >= MAX_CHAPTER_DURATION_SEC
        ):
            full_text = " ".join(current_texts)
            title = generate_chapter_title(full_text)

            chapters.append({
                "start": current_start,
                "end": current_end,
                "title": title,
                "summary": full_text[:200],
            })

            current_start = current_end
            current_texts = []

    # 处理最后一段
    if current_texts:
        full_text = " ".join(current_texts)
        title = generate_chapter_title(full_text)
        chapters.append({
            "start": current_start,
            "end": current_end,
            "title": title,
            "summary": full_text[:200],
        })

    # 合并太短的章节到前一个
    chapters = merge_short_chapters(chapters)

    print(f"[章节分割] 生成 {len(chapters)} 个章节:")
    for i, ch in enumerate(chapters):
        print(f"  Ch{i+1}: [{ch['start']:.1f}s - {ch['end']:.1f}s] {ch['title']}")

    return chapters


def generate_chapter_title(text: str) -> str:
    """从文本中生成章节标题"""
    text = text.strip()

    # 尝试提取第一句有意义的句子作为标题
    sentences = re.split(r'[。！？.!?\n]', text)
    for sentence in sentences:
        sentence = sentence.strip()
        # 跳过太短或太长的句子
        if 5 <= len(sentence) <= 40:
            return sentence

    # 取前30个字符
    if len(text) > 30:
        return text[:30] + "..."
    return text if text else "未命名章节"


def merge_short_chapters(chapters: list, min_duration: int = None) -> list:
    """合并过短的章节到前一个章节"""
    if min_duration is None:
        min_duration = MIN_CHAPTER_DURATION_SEC

    if len(chapters) <= 1:
        return chapters

    merged = []
    for ch in chapters:
        if merged and (ch["end"] - ch["start"]) < min_duration:
            # 合并到前一个章节
            prev = merged[-1]
            prev["end"] = ch["end"]
            prev["summary"] += " " + ch["summary"]
            # 更新标题：如果前一个标题太短，尝试用新标题
            if len(prev["title"]) < 10:
                prev["title"] = ch["title"]
        else:
            merged.append(ch)

    return merged


def analyze_speech(video_path: str, video_duration: float) -> list:
    """
    主函数：分析视频语音，生成章节分段

    返回: [{"start": float, "end": float, "title": str, "summary": str}, ...]
    """
    # 提取音频
    from silence_detector import extract_audio
    audio_path = extract_audio(video_path)

    # 语音转文字
    try:
        transcript = transcribe_audio(audio_path)
    except Exception as e:
        print(f"[语音识别] 失败: {e}")
        print("[语音识别] 将使用默认分段")
        return [{"start": 0, "end": video_duration, "title": "完整视频", "summary": ""}]

    # 分段为章节
    chapters = segment_to_chapters(transcript, video_duration)

    return chapters


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        from silence_detector import get_video_duration
        duration = get_video_duration(sys.argv[1])
        chapters = analyze_speech(sys.argv[1], duration)
        for ch in chapters:
            print(f"  [{ch['start']:.1f}s - {ch['end']:.1f}s] {ch['title']}")
    else:
        print("用法: python speech_to_text.py <video_path>")