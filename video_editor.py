"""
YouTube 口播视频剪辑 - 主编排器 (剪映风格)
===========================================
功能:
1. 智能检测并剪掉停顿过长、无声音的片段 (自适应阈值)
2. 自动语音识别 + 章节分割 (如 whisper 可用)
3. 为每个段落叠加主题文字标签 (淡入动画)
4. 生成 YouTube 风格章节过渡转场页 (含音频特效)
5. 生成可视化进度条 (叠加在视频上方，标注每段主题)
6. 自动生成时间轴报告

用法:
    python video_editor.py <input_video> [--output <output_path>] [选项]
"""

import os
import sys
import subprocess
import json
import argparse
import time
from datetime import timedelta

from config import (
    FFMPEG_PATH, FFPROBE_PATH, TEMP_DIR, OUTPUT_DIR,
    OUTPUT_FPS, OUTPUT_CODEC, OUTPUT_CRF, OUTPUT_PRESET,
    TRANSITION_DURATION_SEC,
    SILENCE_THRESHOLD_DB, SILENCE_MIN_DURATION_MS,
)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def format_time(seconds: float) -> str:
    """格式化时间显示"""
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def print_banner():
    """打印横幅"""
    print("""
 ╔══════════════════════════════════════════════╗
 ║     🎬 智能剪口播 - YouTube 视频剪辑工具     ║
 ║     Smart Cut - 剪映风格智能剪辑             ║
 ╚══════════════════════════════════════════════╝
""")


def cut_video_segments(video_path: str, segments: list, video_info: dict) -> tuple:
    """将视频按段落切割，同时返回各段时长"""
    print("\n[视频切割] 开始切割视频...")
    segment_paths = []
    segment_durations = []

    for i, (start, end) in enumerate(segments):
        output_path = os.path.join(TEMP_DIR, f"segment_{i:03d}.mp4")
        duration = end - start
        segment_durations.append(duration)

        print(f"  段落 {i+1}: {format_time(start)} → {format_time(end)} (时长 {duration:.1f}s)")

        cmd = [
            FFMPEG_PATH, "-y",
            "-ss", str(start),
            "-i", video_path,
            "-t", str(duration),
            "-c:v", "libx264",
            "-c:a", "aac",
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
            "-crf", str(OUTPUT_CRF),
            "-r", str(OUTPUT_FPS),
            "-avoid_negative_ts", "make_zero",
            output_path
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        segment_paths.append(output_path)

    print(f"[视频切割] 完成，共 {len(segment_paths)} 个片段")
    return segment_paths, segment_durations


def build_chapters_from_segments(segments: list, titles: list = None) -> list:
    """从段落构建章节列表"""
    chapters = []
    for i, (s, e) in enumerate(segments):
        title = titles[i] if titles and i < len(titles) else f"段落 {i+1}"
        chapters.append({
            "start": s,
            "end": e,
            "title": title,
            "summary": "",
        })
    return chapters


def build_enhanced_concat_file(
    segment_paths: list,
    transition_videos: list,
    transition_audios: list,
    output_path: str
) -> str:
    """
    构建增强版 FFmpeg concat 文件列表

    结构: [transition_video+audio] → [segment_with_topic] → [transition] → [segment] ...

    使用 concat demuxer，每个文件必须有相同的音视频流
    """
    # 策略: 先给每个转场视频添加音频，然后统一 concat
    concat_entries = []

    for i, seg_path in enumerate(segment_paths):
        if transition_videos and i < len(transition_videos):
            # 转场 + 音频
            trans_vid = transition_videos[i]
            trans_aud = transition_audios[i] if transition_audios and i < len(transition_audios) else None

            if trans_aud:
                # 合并转场视频和音频
                merged_trans = os.path.join(TEMP_DIR, f"transition_merged_{i:03d}.mp4")
                cmd = [
                    FFMPEG_PATH, "-y",
                    "-i", trans_vid,
                    "-i", trans_aud,
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-shortest",
                    merged_trans
                ]
                subprocess.run(cmd, capture_output=True, check=True)
                concat_entries.append(merged_trans)
            else:
                concat_entries.append(trans_vid)

        concat_entries.append(seg_path)

    # 写入 concat 列表
    concat_file = os.path.join(TEMP_DIR, "concat_list.txt")
    with open(concat_file, "w", encoding="utf-8") as f:
        for entry in concat_entries:
            abs_path = os.path.abspath(entry).replace("\\", "/")
            f.write(f"file '{abs_path}'\n")

    return concat_file


def concat_videos_safe(concat_file: str, output_path: str) -> str:
    """安全拼接视频，自动处理流参数不一致的问题"""
    print(f"\n[视频拼接] 拼接所有片段...")

    cmd = [
        FFMPEG_PATH, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_file,
        "-c:v", "libx264",
        "-c:a", "aac",
        "-pix_fmt", "yuv420p",
        "-preset", OUTPUT_PRESET,
        "-crf", str(OUTPUT_CRF),
        "-r", str(OUTPUT_FPS),
        "-vsync", "cfr",
        "-af", "aresample=async=1",
        output_path
    ]
    subprocess.run(cmd, capture_output=True, check=True, text=True)
    print(f"[视频拼接] 完成: {output_path}")
    return output_path


def overlay_progress_bar(video_path: str, progress_bar_path: str, output_path: str) -> str:
    """将进度条叠加到视频上方"""
    print(f"\n[进度条叠加] 叠加进度条到视频...")

    cmd = [
        FFMPEG_PATH, "-y",
        "-i", video_path,
        "-i", progress_bar_path,
        "-filter_complex",
        "[1:v]format=rgba,colorchannelmixer=aa=0.92[bar];[0:v][bar]overlay=0:0:shortest=1",
        "-c:v", "libx264",
        "-c:a", "copy",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        "-crf", str(OUTPUT_CRF),
        output_path
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    print(f"[进度条叠加] 完成: {output_path}")
    return output_path


def calculate_total_duration(
    segments: list,
    use_transitions: bool,
    num_chapters: int
) -> float:
    """计算最终视频总时长"""
    segment_duration = sum(e - s for s, e in segments)
    transition_duration = TRANSITION_DURATION_SEC * num_chapters if use_transitions else 0
    return segment_duration + transition_duration


def generate_timeline_report(
    chapters: list,
    segments: list,
    original_duration: float,
    final_duration: float,
    output_path: str
):
    """生成精美的时间轴报告"""
    report_path = os.path.join(OUTPUT_DIR, "timeline_report.txt")

    lines = []
    lines.append("=" * 65)
    lines.append("    YouTube 智能剪口播 - 时间轴报告")
    lines.append("=" * 65)
    lines.append("")
    lines.append(f"  原始时长:      {format_time(original_duration)}")
    lines.append(f"  最终时长:      {format_time(final_duration)}")
    lines.append(f"  剪除静音:      {format_time(original_duration - final_duration)}")
    if original_duration > 0:
        lines.append(f"  压缩比例:      {(1 - final_duration / original_duration) * 100:.1f}%")
    lines.append("")

    lines.append("-" * 65)
    lines.append(f"  保留段落 ({len(segments)} 段):")
    lines.append("-" * 65)
    for i, (s, e) in enumerate(segments):
        lines.append(f"  #{i+1}: {format_time(s)} → {format_time(e)} (时长 {format_time(e-s)})")

    lines.append("")
    lines.append("-" * 65)
    lines.append(f"  章节划分 ({len(chapters)} 章):")
    lines.append("-" * 65)
    for i, ch in enumerate(chapters):
        lines.append(f"  Ch{i+1}: [{format_time(ch['start'])} → {format_time(ch['end'])}]")
        lines.append(f"         {ch['title']}")

    lines.append("")
    lines.append("=" * 65)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n[报告] 时间轴报告已保存: {report_path}")
    return report_path


def map_chapters_final_timeline(
    chapters: list,
    transition_duration: float,
    num_segments: int
) -> list:
    """
    将章节映射到最终时间轴 (加入转场时间)

    最终时间轴 = 切割后时间 + 每个段落前的转场时间
    """
    if not chapters:
        return chapters

    mapped = []
    accum_offset = 0.0

    for i, ch in enumerate(chapters):
        # 转场时间偏移
        accum_offset += transition_duration

        mapped.append({
            "start": ch["start"] + accum_offset,
            "end": ch["end"] + accum_offset,
            "title": ch["title"],
            "summary": ch.get("summary", ""),
        })

    return mapped


def process_video(
    input_path: str,
    output_path: str = None,
    skip_speech: bool = False,
    no_transition: bool = False,
    no_progress_bar: bool = False,
    no_topic_text: bool = False,
    silence_threshold: float = None,
    min_silence_ms: int = None,
    segment_titles: list = None,
) -> str:
    """
    主处理流程 - 剪映风格智能剪口播

    执行步骤:
    1. 智能静音检测 → 自适应阈值找到最佳切割点
    2. 语音识别 → 章节分割 (可选)
    3. 切割视频 → 按段落切分
    4. 添加主题文字 → 每段叠加主题标签
    5. 生成转场 → 章节过渡动画 + 音频特效
    6. 拼接视频 → 转场 + 段落拼接
    7. 生成进度条 → 可视化进度 + 章节标签
    8. 叠加进度条 → 整合到视频上方
    9. 生成报告 → 时间轴详情
    """
    print_banner()

    t_start = time.time()

    # 确保目录
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if output_path is None:
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(OUTPUT_DIR, f"{base_name}_smartcut.mp4")

    # 覆盖配置
    import config
    if silence_threshold is not None:
        config.SILENCE_THRESHOLD_DB = silence_threshold
    if min_silence_ms is not None:
        config.SILENCE_MIN_DURATION_MS = min_silence_ms

    # ============================================================
    # 步骤 1: 智能静音检测 (自适应阈值)
    # ============================================================
    print("\n" + "━" * 55)
    print("  步骤 1/8: 智能静音检测")
    print("━" * 55)

    from silence_detector import detect_silence_and_get_cuts, get_video_info

    # 先获取视频信息
    video_info = get_video_info(input_path)
    original_duration = video_info["duration"]
    print(f"  视频时长: {format_time(original_duration)}")
    print(f"  分辨率: {video_info['width']}x{video_info['height']}")
    print(f"  帧率: {video_info['fps']:.1f}")

    if not video_info["has_audio"]:
        print("  ⚠ 视频无音轨，将保留全部内容")
        segments = [(0.0, original_duration)]
    else:
        # 自适应静音检测：尝试多个阈值，找到最佳结果
        best_segments = None
        best_score = -1

        thresholds_to_try = [
            (SILENCE_THRESHOLD_DB, SILENCE_MIN_DURATION_MS),
        ]

        # 如果使用默认值，尝试自适应
        if silence_threshold is None and min_silence_ms is None:
            # 根据视频时长调整策略
            if original_duration < 60:
                # 短视频：较激进的检测
                thresholds_to_try = [(-35, 600), (-30, 800)]
            elif original_duration < 300:
                # 中等视频
                thresholds_to_try = [(-35, 800), (-32, 1000)]
            else:
                # 长视频：较保守
                thresholds_to_try = [(-38, 800), (-35, 1000)]

        for thresh, min_sil in thresholds_to_try:
            config.SILENCE_THRESHOLD_DB = thresh
            config.SILENCE_MIN_DURATION_MS = min_sil

            result = detect_silence_and_get_cuts(input_path)
            segs = result["segments"]

            # 评分：保留足够多的内容，但又不是全保留
            kept_ratio = result["total_kept_duration"] / original_duration
            num_segs = len(segs)

            # 理想的保留比例：60%-95%
            if 0.55 <= kept_ratio <= 0.95:
                score = 100 - abs(kept_ratio - 0.80) * 50 + num_segs * 2
            else:
                score = 0

            if score > best_score:
                best_score = score
                best_segments = segs

            print(f"    阈值={thresh}dB, 静音>{min_sil}ms → 保留 {kept_ratio*100:.0f}%, {num_segs}段, 评分={score:.0f}")

        if best_segments is None:
            best_segments = result["segments"]

        segments = best_segments
        print(f"  ✅ 最佳: {len(segments)} 段, 保留 {sum(e-s for s,e in segments)/original_duration*100:.0f}%")

    # ============================================================
    # 步骤 2: 语音识别 & 章节分割
    # ============================================================
    if not skip_speech:
        print("\n" + "━" * 55)
        print("  步骤 2/8: 语音识别与章节分割")
        print("━" * 55)

        try:
            from speech_to_text import analyze_speech
            chapters = analyze_speech(input_path, original_duration)
        except Exception as e:
            print(f"  ⚠ 语音识别失败 ({e})，使用默认分段")
            chapters = build_chapters_from_segments(
                segments,
                segment_titles if segment_titles else None
            )
    else:
        print("\n  ⏭ 跳过语音识别")
        chapters = build_chapters_from_segments(
            segments,
            segment_titles if segment_titles else None
        )

    if not chapters:
        chapters = build_chapters_from_segments(segments, segment_titles)

    use_transitions = not no_transition
    use_topic_text = not no_topic_text
    use_progress = not no_progress_bar

    final_duration = calculate_total_duration(segments, use_transitions, len(chapters))

    # ============================================================
    # 步骤 3: 切割视频段落
    # ============================================================
    print("\n" + "━" * 55)
    print("  步骤 3/8: 切割视频段落")
    print("━" * 55)

    segment_paths, segment_durations = cut_video_segments(input_path, segments, video_info)

    # ============================================================
    # 步骤 4: 添加主题文字
    # ============================================================
    if use_topic_text:
        print("\n" + "━" * 55)
        print("  步骤 4/8: 添加段落主题文字")
        print("━" * 55)

        from text_overlay import add_segment_topics_batch

        # 提取每个段落的主题
        topics = []
        for i, seg_path in enumerate(segment_paths):
            # 从章节中找到对应的标题
            if i < len(chapters):
                title = chapters[i]["title"]
                # 限制长度
                if len(title) > 20:
                    title = title[:19] + "…"
                topics.append(title)
            else:
                topics.append(f"段落 {i+1}")

        segment_paths = add_segment_topics_batch(
            segment_paths, topics, segment_durations
        )
    else:
        print("\n  ⏭ 跳过主题文字")

    # ============================================================
    # 步骤 5: 生成章节过渡转场 (视频 + 音频)
    # ============================================================
    transition_videos = []
    transition_audios = []

    if use_transitions:
        print("\n" + "━" * 55)
        print("  步骤 5/8: 生成章节过渡转场 (视频+音频)")
        print("━" * 55)

        from chapter_transition import generate_all_transitions
        from audio_effects import generate_transition_audio

        transition_videos = generate_all_transitions(
            chapters,
            video_info["width"],
            video_info["height"]
        )

        # 为每个转场生成对应音频
        print("  [音频] 生成转场音效...")
        for i in range(len(transition_videos)):
            audio_path = generate_transition_audio(
                TRANSITION_DURATION_SEC,
                os.path.join(TEMP_DIR, f"transition_audio_{i:03d}.wav")
            )
            transition_audios.append(audio_path)

        print(f"  ✅ 生成 {len(transition_videos)} 个转场 (含音效)")

    # ============================================================
    # 步骤 6: 拼接视频
    # ============================================================
    print("\n" + "━" * 55)
    print("  步骤 6/8: 拼接视频")
    print("━" * 55)

    concat_file = build_enhanced_concat_file(
        segment_paths, transition_videos, transition_audios, output_path
    )
    temp_concat = os.path.join(TEMP_DIR, "concat_output.mp4")
    concat_videos_safe(concat_file, temp_concat)

    # ============================================================
    # 步骤 7: 生成进度条并叠加
    # ============================================================
    if use_progress:
        from progress_bar import generate_progress_bar_video

        print("\n" + "━" * 55)
        print("  步骤 7/8: 生成可视化进度条")
        print("━" * 55)

        # 映射章节到最终时间轴
        final_chapters = map_chapters_final_timeline(
            chapters, TRANSITION_DURATION_SEC if use_transitions else 0,
            len(segment_paths)
        )

        if not final_chapters:
            final_chapters = chapters

        progress_bar_path = generate_progress_bar_video(
            final_chapters,
            final_duration,
            video_info["width"],
            os.path.join(TEMP_DIR, "progress_bar.mp4")
        )

        print("\n" + "━" * 55)
        print("  步骤 8/8: 叠加进度条到视频")
        print("━" * 55)

        overlay_progress_bar(temp_concat, progress_bar_path, output_path)
    else:
        # 直接复制
        import shutil
        shutil.copy2(temp_concat, output_path)
        print("\n  ⏭ 跳过进度条")

    # ============================================================
    # 生成报告
    # ============================================================
    generate_timeline_report(
        chapters,
        segments,
        original_duration,
        final_duration,
        output_path
    )

    # ============================================================
    # 完成
    # ============================================================
    t_elapsed = time.time() - t_start

    print("\n" + "═" * 55)
    print("  ✅ 智能剪口播完成!")
    print("═" * 55)
    print(f"  输出文件:    {output_path}")
    print(f"  原始时长:    {format_time(original_duration)}")
    print(f"  最终时长:    {format_time(final_duration)}")
    if original_duration > 0:
        print(f"  剪除比例:    {(1 - final_duration / original_duration) * 100:.1f}%")
    print(f"  保留段落:    {len(segments)} 段")
    print(f"  章节数量:    {len(chapters)} 章")
    print(f"  转场动画:    {'✓' if use_transitions else '✗'}")
    print(f"  主题文字:    {'✓' if use_topic_text else '✗'}")
    print(f"  进度条:      {'✓' if use_progress else '✗'}")
    print(f"  处理耗时:    {t_elapsed:.1f} 秒")
    print("═" * 55)

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="智能剪口播 - 剪映风格 YouTube 视频剪辑工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python video_editor.py my_video.mp4
  python video_editor.py my_video.mp4 -o output.mp4
  python video_editor.py my_video.mp4 --skip-speech --no-transition
  python video_editor.py my_video.mp4 --silence-threshold -30 --min-silence 500
  python video_editor.py my_video.mp4 --no-progress-bar --no-topic-text
  python video_editor.py my_video.mp4 --titles "开场" "核心内容" "总结"
        """
    )

    parser.add_argument("input", help="输入视频文件路径")
    parser.add_argument("--output", "-o", help="输出视频文件路径")
    parser.add_argument("--skip-speech", action="store_true", help="跳过语音识别")
    parser.add_argument("--no-transition", action="store_true", help="不生成章节转场")
    parser.add_argument("--no-progress-bar", action="store_true", help="不生成进度条")
    parser.add_argument("--no-topic-text", action="store_true", help="不添加段落主题文字")
    parser.add_argument("--silence-threshold", type=float, default=None,
                        help="静音阈值 dB (默认: -35, 建议 -20 ~ -50)")
    parser.add_argument("--min-silence", type=int, default=None,
                        help="最短静音时长 ms (默认: 800, 建议 300~2000)")
    parser.add_argument("--titles", nargs="*", default=None,
                        help="自定义段落标题 (空格分隔)")

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"❌ 错误: 找不到输入文件 {args.input}")
        sys.exit(1)

    process_video(
        input_path=args.input,
        output_path=args.output,
        skip_speech=args.skip_speech,
        no_transition=args.no_transition,
        no_progress_bar=args.no_progress_bar,
        no_topic_text=args.no_topic_text,
        silence_threshold=args.silence_threshold,
        min_silence_ms=args.min_silence,
        segment_titles=args.titles,
    )


if __name__ == "__main__":
    main()