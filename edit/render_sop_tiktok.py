import importlib.util
import math
import shutil
import subprocess
import sys
import wave
from array import array
from pathlib import Path
from typing import Sequence, TypedDict


class Scene(TypedDict):
    start_s: float
    end_s: float
    th: str
    en: str


SCENES: list[Scene] = [
    {
        "start_s": 0,
        "end_s": 3,
        "th": "ธุรกิจบริการพร้อมเติบโตทุกสาขาหรือยังคะ?",
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

NARRATION_TH = (
    "ธุรกิจบริการของคุณ พร้อมเติบโตทุกสาขาหรือยังคะ? "
    "อาร์แอนด์บี ทานโซลูชั่น ออกแบบ เอส โอ พี ให้เหมาะกับธุรกิจของคุณ "
    "ทั้งขั้นตอนบริการ เช็กลิสต์ และสูตรมาตรฐาน "
    "พร้อมเวิร์กช็อปฝึกทีม เพื่อให้บริการสม่ำเสมอและเติบโตอย่างมั่นใจ "
    "นัดหมายปรึกษาฟรี กับอาร์แอนด์บี ทานโซลูชั่นค่ะ"
)

TTS_VOICE = "th-TH-NiwatNeural"
TTS_RATE = "+5%"
SAMPLE_RATE = 48000


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


def render_audio(output_dir: Path) -> tuple[Path, Path]:
    preflight_audio_tools()
    output_dir.mkdir(parents=True, exist_ok=True)
    voice_mp3 = output_dir / "voice.mp3"
    voice_wav = output_dir / "voice.wav"
    music_wav = output_dir / "music.wav"

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
                NARRATION_TH,
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
                str(voice_wav),
            ],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        detail = getattr(exc, "stderr", None) or str(exc)
        raise RuntimeError(f"Thai narration generation/conversion failed: {detail}") from exc

    if not voice_wav.is_file() or voice_wav.stat().st_size == 0:
        raise RuntimeError("Thai narration conversion produced no audio")
    if _wav_duration(voice_wav) > total_duration_s() - 1:
        raise ValueError("Thai narration must finish at least one second before the video ends")

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
