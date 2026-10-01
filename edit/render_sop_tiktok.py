import importlib.util
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import wave
from array import array
from functools import lru_cache
from pathlib import Path
from typing import Sequence, TypedDict

from PIL import Image, ImageDraw, ImageFont, ImageOps


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SUITE_IMAGE_PATH = PROJECT_ROOT / "assets" / "sop_suite_mockup.jpg"
FLOWCHART_IMAGE_PATH = PROJECT_ROOT / "assets" / "sop_flowchart_mockup.jpg"
TITLE_FONT_PATH = Path("/Users/ittmacair/Library/Fonts/ThaiSansNeue-Bold.ttf")
BODY_FONT_PATH = Path("/Users/ittmacair/Library/Fonts/THSarabun Bold.ttf")

FRAME_WIDTH = 1080
FRAME_HEIGHT = 1920
FPS = 30
SAMPLE_RATE = 48000

DEEP_GREEN = (18, 49, 43)
DEEPER_GREEN = (13, 39, 35)
CHAMPAGNE = (218, 193, 145)
CREAM = (247, 243, 233)
PALE_GREEN = (214, 226, 216)
INK = (29, 51, 46)

LAYOUT_BOXES = {
    "header": (70, 275, 820, 470),
    "visual": (70, 500, 820, 1160),
    "captions": (70, 1200, 820, 1370),
    "cta": (90, 560, 800, 1100),
}

_RESAMPLE = getattr(Image, "Resampling", Image).LANCZOS


class Scene(TypedDict):
    start_s: float
    end_s: float
    th: str
    en: str


SCENES: list[Scene] = [
    {
        "start_s": 0,
        "end_s": 3,
        "th": "ธุรกิจพร้อมเติบโตหรือยังครับ?",
        "en": "READY TO SCALE?",
    },
    {
        "start_s": 3,
        "end_s": 7,
        "th": "มาตรฐานที่ออกแบบเพื่อธุรกิจคุณ",
        "en": "R&B SOP STANDARD",
    },
    {
        "start_s": 7,
        "end_s": 13,
        "th": "คู่มือที่ทีมใช้ได้จริง",
        "en": "PRACTICAL SOPs",
    },
    {
        "start_s": 13,
        "end_s": 19,
        "th": "ขั้นตอนบริการ • เช็กลิสต์ • สูตรมาตรฐาน",
        "en": "WORKFLOWS • CHECKLISTS • RECIPES",
    },
    {
        "start_s": 19,
        "end_s": 24,
        "th": "อบรมทีม • ยกระดับมาตรฐาน",
        "en": "TRAIN TEAMS • IMPROVE CONSISTENCY",
    },
    {
        "start_s": 24,
        "end_s": 30,
        "th": "นัดหมายปรึกษาฟรี",
        "en": "BOOK A FREE CONSULTATION",
    },
]

NARRATION_BY_SCENE = (
    "ธุรกิจพร้อมเติบโตหรือยังครับ?",
    "ออกแบบ เอส โอ พี ให้เหมาะกับธุรกิจคุณ",
    "คู่มือที่ทีมใช้ได้จริง",
    "ขั้นตอนบริการ เช็กลิสต์ และสูตรมาตรฐาน",
    "ฝึกทีมให้บริการสม่ำเสมอ พร้อมเติบโตมั่นใจ",
    "นัดหมายปรึกษาฟรี กับอาร์แอนด์บี ทานโซลูชั่นครับ",
)
NARRATION_TH = " ".join(NARRATION_BY_SCENE)

TTS_VOICE = "th-TH-NiwatNeural"
TTS_RATE = "+5%"


def total_duration_s() -> float:
    return SCENES[-1]["end_s"]


def validate_timeline(scenes: Sequence[Scene]) -> None:
    if not scenes:
        raise ValueError("Timeline must contain at least one scene")

    expected_start = 0
    for scene in scenes:
        start_s = scene["start_s"]
        end_s = scene["end_s"]
        if not isinstance(start_s, (int, float)) or not isinstance(end_s, (int, float)):
            raise ValueError("Scene boundaries must be numeric")
        if start_s != expected_start or end_s <= start_s:
            raise ValueError("Scenes must be positive-length, ordered, and contiguous from zero")
        if not scene["th"].strip() or not scene["en"].strip():
            raise ValueError("Each scene must include Thai and English copy")
        expected_start = end_s

    if not 25 <= expected_start <= 30:
        raise ValueError("Timeline duration must be between 25 and 30 seconds")


def preflight_audio_tools() -> None:
    if not shutil.which("python3"):
        raise RuntimeError("python3 is required for Thai voice generation")
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is required for audio conversion and mixing")
    if importlib.util.find_spec("edge_tts") is None:
        raise RuntimeError("The edge-tts Python module is required for Thai narration")

    try:
        voices = subprocess.run(
            [sys.executable, "-m", "edge_tts", "--list-voices"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("Could not verify the required Edge TTS voice") from exc

    if TTS_VOICE not in voices.stdout:
        raise RuntimeError(f"Required Thai Edge TTS voice is unavailable: {TTS_VOICE}")


def create_instrumental(output_path: Path, duration_s: float = 30) -> Path:
    sample_count = round(SAMPLE_RATE * duration_s)
    chord_sets = (
        (130.81, 164.81, 196.00, 246.94),
        (110.00, 130.81, 164.81, 196.00),
        (87.31, 110.00, 130.81, 174.61),
        (98.00, 123.47, 146.83, 196.00),
    )
    melody = (261.63, 293.66, 329.63, 392.00, 440.00, 392.00, 329.63, 293.66)
    beat_s = 0.75
    samples = array("h")

    for index in range(sample_count):
        time_s = index / SAMPLE_RATE
        chord_index = min(int(time_s / 7.5), len(chord_sets) - 1)
        chord = chord_sets[chord_index]
        pad = sum(math.sin(2 * math.pi * frequency * time_s) for frequency in chord) * 0.045

        beat_index = int(time_s / beat_s)
        beat_phase = time_s - beat_index * beat_s
        note = melody[(beat_index * 3) % len(melody)]
        envelope = math.exp(-beat_phase * 4)
        pluck = (
            math.sin(2 * math.pi * note * time_s)
            + 0.22 * math.sin(4 * math.pi * note * time_s)
        ) * envelope * 0.11
        pulse = math.sin(2 * math.pi * 65.41 * time_s) * 0.018
        fade_in = min(1.0, time_s / 0.8)
        fade_out = min(1.0, (duration_s - time_s) / 1.0)
        sample = max(-0.6, min(0.6, (pad + pluck + pulse) * fade_in * fade_out))
        integer_sample = round(sample * 32767)
        samples.extend((integer_sample, integer_sample))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), "wb") as music:
        music.setnchannels(2)
        music.setsampwidth(2)
        music.setframerate(SAMPLE_RATE)
        music.writeframes(samples.tobytes())
    return output_path


def _wav_duration(path: Path) -> float:
    with wave.open(str(path), "rb") as audio:
        if audio.getframerate() <= 0:
            raise ValueError(f"Invalid audio sample rate: {path}")
        return audio.getnframes() / audio.getframerate()


def assemble_narration_by_scene(clip_paths: Sequence[Path], output_path: Path) -> Path:
    if len(clip_paths) != len(SCENES):
        raise ValueError("Narration must contain exactly one audio clip per scene")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    previous_end_frame = 0
    with wave.open(str(output_path), "wb") as narration:
        narration.setnchannels(1)
        narration.setsampwidth(2)
        narration.setframerate(SAMPLE_RATE)

        for index, (scene, clip_path) in enumerate(zip(SCENES, clip_paths)):
            try:
                with wave.open(str(clip_path), "rb") as clip:
                    if (
                        clip.getnchannels() != 1
                        or clip.getsampwidth() != 2
                        or clip.getframerate() != SAMPLE_RATE
                    ):
                        raise ValueError(f"Narration clip must be mono 48 kHz PCM: {clip_path.name}")
                    clip_frames = clip.getnframes()
                    clip_duration = clip_frames / SAMPLE_RATE
                    scene_duration = scene["end_s"] - scene["start_s"]
                    if clip_duration > scene_duration:
                        raise ValueError(
                            f"Narration clip for scene {index + 1} exceeds its "
                            f"{scene_duration:g}-second window"
                        )
                    start_frame = round(scene["start_s"] * SAMPLE_RATE)
                    if start_frame < previous_end_frame:
                        raise ValueError("Narration clips overlap their storyboard scenes")
                    narration.writeframes(b"\x00\x00" * (start_frame - previous_end_frame))
                    narration.writeframes(clip.readframes(clip_frames))
                    previous_end_frame = start_frame + clip_frames
            except (OSError, wave.Error) as exc:
                raise RuntimeError(
                    f"Could not read narration clip for scene {index + 1}: {clip_path.name}"
                ) from exc

    if _wav_duration(output_path) > total_duration_s() - 1:
        output_path.unlink(missing_ok=True)
        raise ValueError("Narration must finish at least one second before the video ends")
    return output_path


def render_audio(output_dir: Path) -> tuple[Path, Path]:
    preflight_audio_tools()
    output_dir.mkdir(parents=True, exist_ok=True)
    voice_wav = output_dir / "voice.wav"
    music_wav = output_dir / "music.wav"
    clip_wavs = []

    for index, text in enumerate(NARRATION_BY_SCENE):
        voice_mp3 = output_dir / f"voice-{index + 1}.mp3"
        clip_wav = output_dir / f"voice-{index + 1}.wav"
        try:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "edge_tts",
                    "--voice",
                    TTS_VOICE,
                    f"--rate={TTS_RATE}",
                    "--text",
                    text,
                    "--write-media",
                    str(voice_mp3),
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=90,
            )
            subprocess.run(
                [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    str(voice_mp3),
                    "-ac",
                    "1",
                    "-ar",
                    str(SAMPLE_RATE),
                    "-c:a",
                    "pcm_s16le",
                    str(clip_wav),
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            detail = getattr(exc, "stderr", None) or str(exc)
            raise RuntimeError(
                f"Thai narration generation/conversion failed for scene {index + 1}: {detail}"
            ) from exc

        if not clip_wav.is_file() or clip_wav.stat().st_size == 0:
            raise RuntimeError(f"Thai narration conversion produced no audio for scene {index + 1}")
        clip_wavs.append(clip_wav)

    assemble_narration_by_scene(clip_wavs, voice_wav)

    create_instrumental(music_wav, duration_s=total_duration_s())
    return voice_wav, music_wav


def mix_audio(
    voice_path: Path,
    music_path: Path,
    output_path: Path,
    duration_s: float,
) -> Path:
    if not voice_path.is_file() or not music_path.is_file():
        raise FileNotFoundError("Both narration and instrumental WAV files are required")
    if duration_s <= 1 or _wav_duration(voice_path) > duration_s - 1:
        raise ValueError("Narration must leave at least one second for the video end card")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    filter_graph = (
        "[0:a]aformat=sample_rates=48000:channel_layouts=stereo,"
        "volume=0.95,afade=t=in:st=0:d=0.03,asplit=2[voice][sidechain];"
        "[1:a]volume=0.14,afade=t=in:st=0:d=0.8,"
        f"afade=t=out:st={max(0, duration_s - 1):.3f}:d=1[bed];"
        f"[sidechain]apad=whole_dur={duration_s:.3f}[sidechain_padded];"
        "[bed][sidechain_padded]sidechaincompress=threshold=0.025:ratio=6:"
        "attack=20:release=250[ducked];"
        "[ducked][voice]amix=inputs=2:duration=longest:normalize=0,"
        "alimiter=limit=0.85,"
        f"afade=t=out:st={max(0, duration_s - 0.03):.3f}:d=0.03[out]"
    )
    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(voice_path),
        "-i",
        str(music_path),
        "-filter_complex",
        filter_graph,
        "-map",
        "[out]",
        "-t",
        str(duration_s),
        "-ar",
        str(SAMPLE_RATE),
        "-ac",
        "2",
        "-c:a",
        "pcm_s16le",
        str(output_path),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=60)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        output_path.unlink(missing_ok=True)
        detail = getattr(exc, "stderr", None) or str(exc)
        raise RuntimeError(f"Audio mix failed: {detail}") from exc

    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError("Audio mixer produced no output")
    return output_path


@lru_cache(maxsize=1)
def _load_visual_assets(
    suite_path: Path,
    flowchart_path: Path,
    title_font_path: Path,
    body_font_path: Path,
) -> tuple[Image.Image, Image.Image, Path, Path]:
    images: list[Image.Image] = []
    for path in (suite_path, flowchart_path):
        try:
            with Image.open(path) as source:
                source.load()
                images.append(source.convert("RGB"))
        except (OSError, ValueError) as exc:
            raise RuntimeError(f"Required visual asset is missing or unreadable: {path.name}") from exc

    for path in (title_font_path, body_font_path):
        try:
            ImageFont.truetype(str(path), 36)
        except OSError as exc:
            raise RuntimeError(f"Required Thai font is missing or unreadable: {path.name}") from exc

    return images[0], images[1], title_font_path, body_font_path


def preflight_visual_assets() -> None:
    _load_visual_assets(
        SUITE_IMAGE_PATH,
        FLOWCHART_IMAGE_PATH,
        TITLE_FONT_PATH,
        BODY_FONT_PATH,
    )


@lru_cache(maxsize=32)
def _font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def _fit_font(text: str, path: Path, max_width: int, preferred_size: int) -> ImageFont.FreeTypeFont:
    size = preferred_size
    while size > 20:
        font = _font(path, size)
        if font.getbbox(text)[2] <= max_width:
            return font
        size -= 2
    return _font(path, size)


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    y: int,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int],
    left: int = 80,
    right: int = 820,
) -> None:
    text_width = draw.textbbox((0, 0), text, font=font)[2]
    x = left + max(0, (right - left - text_width) // 2)
    draw.text((x, y), text, font=font, fill=fill)


def _draw_panel(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    fill: tuple[int, int, int],
    outline: tuple[int, int, int] = CHAMPAGNE,
    radius: int = 24,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=2)


def _draw_image_card(
    frame: Image.Image,
    source: Image.Image,
    box: tuple[int, int, int, int],
    progress: float,
) -> None:
    left, top, right, bottom = box
    width = right - left
    height = bottom - top
    inset = 10
    draw = ImageDraw.Draw(frame)
    shifted_box = (left, top, right, bottom)
    _draw_panel(draw, shifted_box, CREAM, outline=CHAMPAGNE, radius=26)
    inner_size = (width - inset * 2, height - inset * 2)
    zoom = 1.0 + 0.025 * progress
    zoomed = source.resize(
        (round(source.width * zoom), round(source.height * zoom)),
        _RESAMPLE,
    )
    image = ImageOps.fit(zoomed, inner_size, method=_RESAMPLE, centering=(0.5, 0.48))
    mask = Image.new("L", inner_size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, inner_size[0] - 1, inner_size[1] - 1),
        radius=18,
        fill=255,
    )
    frame.paste(image, (left + inset, top + inset), mask)


def _scene_progress(time_s: float, scene_index: int) -> float:
    scene = SCENES[scene_index]
    return min(1.0, max(0.0, (time_s - scene["start_s"]) / (scene["end_s"] - scene["start_s"])))


def ease_out_cubic(value: float) -> float:
    t = min(1.0, max(0.0, value))
    return 1 - (1 - t) ** 3


def scene_index_at(time_s: float) -> int:
    if not math.isfinite(time_s):
        raise ValueError("Scene time must be finite")
    if time_s <= SCENES[0]["start_s"]:
        return 0
    if time_s >= total_duration_s():
        return len(SCENES) - 1
    for index, scene in enumerate(SCENES):
        if scene["start_s"] <= time_s < scene["end_s"]:
            return index
    return len(SCENES) - 1


def _draw_header(frame: Image.Image, title_font_path: Path, body_font_path: Path) -> None:
    draw = ImageDraw.Draw(frame)
    draw.text((76, 284), "R&B TRANSOLUTION", font=_font(body_font_path, 29), fill=CHAMPAGNE)
    title = "SOP STANDARD"
    title_font = _fit_font(title, title_font_path, 720, 68)
    draw.text((75, 330), title, font=title_font, fill=CREAM)
    draw.rounded_rectangle((76, 425, 295, 431), radius=3, fill=CHAMPAGNE)


def _draw_opening_flow(frame: Image.Image, progress: float, body_font_path: Path) -> None:
    draw = ImageDraw.Draw(frame)
    labels = ("SERVICE", "TEAM", "STANDARD")
    boxes = ((100, 635, 302, 790), (350, 635, 552, 790), (600, 635, 802, 790))
    line_y = 712
    for index, (label, box) in enumerate(zip(labels, boxes)):
        _draw_panel(draw, box, DEEPER_GREEN)
        label_font = _fit_font(label, body_font_path, 176, 34)
        _draw_centered_text(draw, label, box[1] + 54, label_font, CREAM, box[0] + 12, box[2] - 12)
        if index < 2:
            line_progress = ease_out_cubic(max(0, min(1, (progress - index * 0.16) / 0.22)))
            start_x = box[2] + 8
            end_x = boxes[index + 1][0] - 8
            draw.line((start_x, line_y, start_x + (end_x - start_x) * line_progress, line_y), fill=CHAMPAGNE, width=4)

    draw.rounded_rectangle((156, 900, 746, 1000), radius=26, fill=(26, 69, 59), outline=CHAMPAGNE, width=2)
    _draw_centered_text(draw, "ONE CLEAR WAY TO SERVE", 923, _font(body_font_path, 33), PALE_GREEN, 176, 726)


def _draw_brand_card(frame: Image.Image, progress: float, title_font_path: Path, body_font_path: Path) -> None:
    draw = ImageDraw.Draw(frame)
    _draw_panel(draw, (112, 560, 778, 1105), DEEPER_GREEN, radius=32)
    eased = ease_out_cubic(min(1.0, progress / 0.55))
    center = (445, 765)
    radius = round(122 * eased)
    draw.ellipse(
        (center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius),
        outline=CHAMPAGNE,
        width=4,
    )
    _draw_centered_text(draw, "R&B", 698, _font(title_font_path, 78), CREAM)
    _draw_centered_text(draw, "HOSPITALITY SOP STANDARD", 879, _fit_font("HOSPITALITY SOP STANDARD", body_font_path, 570, 39), CHAMPAGNE)
    draw.line((235, 965, 655, 965), fill=(85, 122, 103), width=2)
    _draw_centered_text(draw, "BUILT AROUND YOUR OPERATIONS", 987, _fit_font("BUILT AROUND YOUR OPERATIONS", body_font_path, 560, 34), PALE_GREEN)


def _draw_mockup_scene(
    frame: Image.Image,
    suite_image: Image.Image,
    flowchart_image: Image.Image,
    progress: float,
) -> None:
    entrance = round((1 - ease_out_cubic(min(1.0, progress / 0.45))) * 55)
    _draw_image_card(frame, suite_image, (88, 520 + entrance, 760, 870 + entrance), progress)
    _draw_image_card(frame, flowchart_image, (150, 785 + entrance, 820, 1135 + entrance), progress)


def _draw_workflow_scene(
    frame: Image.Image,
    flowchart_image: Image.Image,
    progress: float,
    body_font_path: Path,
) -> None:
    entrance = round((1 - ease_out_cubic(min(1.0, progress / 0.45))) * 48)
    _draw_image_card(frame, flowchart_image, (90, 520 + entrance, 810, 955 + entrance), progress)
    draw = ImageDraw.Draw(frame)
    chips = (("WORKFLOWS", 90, 326), ("CHECKLISTS", 340, 576), ("RECIPES", 590, 810))
    for index, (label, left, right) in enumerate(chips):
        reveal = ease_out_cubic(max(0, min(1, (progress - index * 0.12) / 0.3)))
        if reveal <= 0:
            continue
        box = (left, 1015 + entrance, right, 1110 + entrance)
        _draw_panel(draw, box, DEEPER_GREEN)
        _draw_centered_text(
            draw,
            label,
            box[1] + 24,
            _fit_font(label, body_font_path, right - left - 20, 32),
            CREAM,
            left + 8,
            right - 8,
        )


def _draw_training_scene(
    frame: Image.Image,
    suite_image: Image.Image,
    progress: float,
    body_font_path: Path,
) -> None:
    entrance = round((1 - ease_out_cubic(min(1.0, progress / 0.4))) * 45)
    _draw_image_card(frame, suite_image, (82, 575 + entrance, 505, 900 + entrance), progress)
    draw = ImageDraw.Draw(frame)
    steps = ("SHOW", "PRACTICE", "ALIGN")
    for index, text in enumerate(steps):
        top = 590 + index * 170 + entrance
        _draw_panel(draw, (555, top, 810, top + 116), DEEPER_GREEN)
        draw.ellipse((578, top + 34, 616, top + 72), outline=CHAMPAGNE, width=3)
        draw.line((588, top + 53, 599, top + 64, 613, top + 42), fill=PALE_GREEN, width=3)
        _draw_centered_text(draw, text, top + 70, _fit_font(text, body_font_path, 190, 32), CREAM, 625, 800)


def _draw_cta_scene(frame: Image.Image, title_font_path: Path, body_font_path: Path) -> None:
    draw = ImageDraw.Draw(frame)
    box = LAYOUT_BOXES["cta"]
    _draw_panel(draw, box, DEEPER_GREEN, radius=34)
    draw.ellipse((330, 620, 560, 850), outline=CHAMPAGNE, width=4)
    _draw_centered_text(draw, "R&B", 675, _font(title_font_path, 76), CREAM)
    _draw_centered_text(draw, "A CLEARER WAY TO WORK", 887, _font(body_font_path, 36), PALE_GREEN)
    draw.line((235, 953, 655, 953), fill=(85, 122, 103), width=2)
    _draw_centered_text(draw, "LINE  @rnbtransolution", 979, _font(body_font_path, 40), CHAMPAGNE)


def _draw_scene_art(
    frame: Image.Image,
    scene_index: int,
    progress: float,
    suite_image: Image.Image,
    flowchart_image: Image.Image,
    title_font_path: Path,
    body_font_path: Path,
) -> None:
    if scene_index == 0:
        _draw_opening_flow(frame, progress, body_font_path)
    elif scene_index == 1:
        _draw_brand_card(frame, progress, title_font_path, body_font_path)
    elif scene_index == 2:
        _draw_mockup_scene(frame, suite_image, flowchart_image, progress)
    elif scene_index == 3:
        _draw_workflow_scene(frame, flowchart_image, progress, body_font_path)
    elif scene_index == 4:
        _draw_training_scene(frame, suite_image, progress, body_font_path)
    else:
        _draw_cta_scene(frame, title_font_path, body_font_path)


def _draw_captions(
    frame: Image.Image,
    scene: Scene,
    progress: float,
    body_font_path: Path,
) -> Image.Image:
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    alpha = round(242 * ease_out_cubic(min(1.0, progress / 0.18)))
    left, top, right, bottom = LAYOUT_BOXES["captions"]
    draw.rounded_rectangle(
        (left, top, right, bottom),
        radius=22,
        fill=(13, 39, 35, alpha),
        outline=(*CHAMPAGNE, alpha),
        width=2,
    )
    thai_font = _fit_font(scene["th"], body_font_path, right - left - 38, 58)
    english_font = _fit_font(scene["en"], body_font_path, right - left - 38, 34)
    _draw_centered_text(draw, scene["th"], top + 14, thai_font, (*CREAM, alpha), left + 18, right - 18)
    _draw_centered_text(draw, scene["en"], top + 86, english_font, (*CHAMPAGNE, alpha), left + 18, right - 18)
    return Image.alpha_composite(frame.convert("RGBA"), overlay).convert("RGB")


def render_frame(time_s: float) -> Image.Image:
    if not math.isfinite(time_s):
        raise ValueError("Frame time must be finite")
    suite_image, flowchart_image, title_font_path, body_font_path = _load_visual_assets(
        SUITE_IMAGE_PATH,
        FLOWCHART_IMAGE_PATH,
        TITLE_FONT_PATH,
        BODY_FONT_PATH,
    )
    safe_time = min(total_duration_s(), max(0.0, time_s))
    scene_index = scene_index_at(safe_time)
    progress = _scene_progress(safe_time, scene_index)

    frame = Image.new("RGB", (FRAME_WIDTH, FRAME_HEIGHT), DEEP_GREEN)
    _draw_header(frame, title_font_path, body_font_path)
    _draw_scene_art(
        frame,
        scene_index,
        progress,
        suite_image,
        flowchart_image,
        title_font_path,
        body_font_path,
    )
    return _draw_captions(frame, SCENES[scene_index], progress, body_font_path)


def _verify_render(path: Path) -> None:
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=codec_type,width,height,sample_rate",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    metadata = json.loads(probe.stdout)
    streams = metadata.get("streams", [])
    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    duration = float(metadata["format"]["duration"])
    if video_stream is None or audio_stream is None:
        raise RuntimeError("Rendered MP4 must contain video and audio streams")
    if (video_stream.get("width"), video_stream.get("height")) != (FRAME_WIDTH, FRAME_HEIGHT):
        raise RuntimeError("Rendered MP4 has incorrect video dimensions")
    if int(audio_stream.get("sample_rate", 0)) != SAMPLE_RATE:
        raise RuntimeError("Rendered MP4 audio must use a 48 kHz sample rate")
    if not 25 <= duration <= 30:
        raise RuntimeError(f"Rendered MP4 duration must be 25–30 seconds, got {duration:.2f}")


def render_video(output_path: Path) -> Path:
    output_path = Path(output_path)
    validate_timeline(SCENES)
    preflight_visual_assets()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_video: Path | None = None
    encoder: subprocess.Popen | None = None
    success = False

    try:
        with tempfile.TemporaryDirectory(prefix=".sop-audio-", dir=output_path.parent) as working_dir:
            voice_path, music_path = render_audio(Path(working_dir))
            mixed_audio = mix_audio(
                voice_path,
                music_path,
                Path(working_dir) / "mix.wav",
                total_duration_s(),
            )
            with tempfile.NamedTemporaryFile(
                prefix=f".{output_path.stem}.",
                suffix=".tmp.mp4",
                dir=output_path.parent,
                delete=False,
            ) as temporary_file:
                temporary_video = Path(temporary_file.name)

            command = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-f",
                "rawvideo",
                "-pixel_format",
                "rgb24",
                "-video_size",
                f"{FRAME_WIDTH}x{FRAME_HEIGHT}",
                "-framerate",
                str(FPS),
                "-i",
                "pipe:0",
                "-i",
                str(mixed_audio),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "19",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-ar",
                str(SAMPLE_RATE),
                "-t",
                str(total_duration_s()),
                "-movflags",
                "+faststart",
                str(temporary_video),
            ]
            encoder = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            if encoder.stdin is None:
                raise RuntimeError("FFmpeg did not open its video input")
            for frame_index in range(round(total_duration_s() * FPS)):
                frame = render_frame(frame_index / FPS)
                encoder.stdin.write(frame.convert("RGB").tobytes())
            encoder.stdin.close()
            error_output = encoder.stderr.read() if encoder.stderr is not None else b""
            return_code = encoder.wait()
            if return_code != 0:
                detail = error_output.decode("utf-8", "replace").strip()
                raise RuntimeError(f"FFmpeg video encoding failed: {detail or return_code}")

        if temporary_video is None or not temporary_video.is_file() or temporary_video.stat().st_size == 0:
            raise RuntimeError("FFmpeg produced no video output")
        _verify_render(temporary_video)
        os.replace(temporary_video, output_path)
        success = True
        return output_path
    except RuntimeError:
        raise
    except (OSError, subprocess.SubprocessError, ValueError, KeyError) as exc:
        raise RuntimeError(f"Video render failed: {exc}") from exc
    finally:
        if encoder is not None and encoder.poll() is None:
            if encoder.stdin is not None and not encoder.stdin.closed:
                encoder.stdin.close()
            encoder.terminate()
            encoder.wait()
        if not success and temporary_video is not None:
            temporary_video.unlink(missing_ok=True)
