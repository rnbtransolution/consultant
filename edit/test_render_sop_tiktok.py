import unittest
import subprocess
import tempfile
import wave
from pathlib import Path
from unittest.mock import patch

from edit.render_sop_tiktok import (
    NARRATION_TH,
    SCENES,
    create_instrumental,
    mix_audio,
    preflight_audio_tools,
    render_audio,
    total_duration_s,
    validate_timeline,
)


class TimelineTests(unittest.TestCase):
    def test_scenes_match_the_approved_six_beat_storyboard(self):
        expected_bounds = [(0, 3), (3, 7), (7, 13), (13, 19), (19, 24), (24, 30)]

        self.assertEqual(
            [(scene["start_s"], scene["end_s"]) for scene in SCENES],
            expected_bounds,
        )
        self.assertTrue(all(scene["th"].strip() and scene["en"].strip() for scene in SCENES))
        self.assertIn("อาร์แอนด์บี ทานโซลูชั่น", NARRATION_TH)
        self.assertIn("เอส โอ พี", NARRATION_TH)
        validate_timeline(SCENES)

    def test_total_duration_is_thirty_seconds(self):
        self.assertEqual(total_duration_s(), 30)

    def test_rejects_an_empty_timeline(self):
        with self.assertRaises(ValueError):
            validate_timeline([])

    def test_rejects_zero_length_scene(self):
        scenes = [dict(SCENES[0]), dict(SCENES[1])]
        scenes[0]["end_s"] = scenes[0]["start_s"]

        with self.assertRaises(ValueError):
            validate_timeline(scenes)

    def test_rejects_overlapping_scenes(self):
        scenes = [dict(SCENES[0]), dict(SCENES[1])]
        scenes[1]["start_s"] = scenes[0]["end_s"] - 0.1

        with self.assertRaises(ValueError):
            validate_timeline(scenes)

    def test_rejects_gaps_and_out_of_order_scenes(self):
        scenes = [dict(SCENES[0]), dict(SCENES[1])]
        scenes[1]["start_s"] += 0.1

        with self.assertRaises(ValueError):
            validate_timeline(scenes)

        scenes = [dict(SCENES[1]), dict(SCENES[0])]
        with self.assertRaises(ValueError):
            validate_timeline(scenes)

    def test_rejects_timeline_longer_than_thirty_seconds(self):
        scenes = [dict(scene) for scene in SCENES]
        scenes[-1]["end_s"] = 30.1

        with self.assertRaises(ValueError):
            validate_timeline(scenes)


class AudioTests(unittest.TestCase):
    @patch("edit.render_sop_tiktok.subprocess.run")
    @patch("edit.render_sop_tiktok.importlib.util.find_spec", return_value=object())
    @patch("edit.render_sop_tiktok.shutil.which")
    def test_audio_preflight_requires_edge_tts_and_ffmpeg(
        self, which, find_spec, run
    ):
        which.side_effect = lambda command: None if command == "ffmpeg" else "/usr/bin/python3"

        with self.assertRaisesRegex(RuntimeError, "ffmpeg"):
            preflight_audio_tools()

        run.assert_not_called()

    @patch("edit.render_sop_tiktok.subprocess.run")
    @patch("edit.render_sop_tiktok.importlib.util.find_spec", return_value=object())
    @patch("edit.render_sop_tiktok.shutil.which", return_value="/usr/bin/tool")
    def test_audio_preflight_requires_configured_thai_voice(
        self, which, find_spec, run
    ):
        run.return_value = subprocess.CompletedProcess(
            args=["python3", "-m", "edge_tts", "--list-voices"],
            returncode=0,
            stdout="en-US-AriaNeural\n",
            stderr="",
        )

        with self.assertRaisesRegex(RuntimeError, "th-TH-NiwatNeural"):
            preflight_audio_tools()

    @patch("edit.render_sop_tiktok.preflight_audio_tools")
    @patch("edit.render_sop_tiktok.subprocess.run")
    def test_edge_tts_failure_is_reported(self, run, preflight):
        run.side_effect = subprocess.CalledProcessError(
            1,
            ["python3", "-m", "edge_tts"],
            stderr="TTS unavailable",
        )

        with tempfile.TemporaryDirectory() as temporary_dir:
            with self.assertRaisesRegex(RuntimeError, "TTS"):
                render_audio(Path(temporary_dir))

        self.assertIn("--rate=+5%", run.call_args.args[0])
        self.assertIn("th-TH-NiwatNeural", run.call_args.args[0])

    def test_instrumental_is_audible_stereo_48khz_wav(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            music_path = Path(temporary_dir) / "music.wav"
            create_instrumental(music_path, duration_s=2)

            with wave.open(str(music_path), "rb") as music:
                self.assertEqual(music.getnchannels(), 2)
                self.assertEqual(music.getframerate(), 48000)
                self.assertEqual(music.getnframes(), 96000)
                self.assertGreater(music.getsampwidth(), 0)

    def test_mix_keeps_the_music_bed_for_the_full_video_duration(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            directory = Path(temporary_dir)
            voice_path = directory / "voice.wav"
            music_path = create_instrumental(directory / "music.wav", duration_s=2)
            output_path = directory / "mix.wav"
            with wave.open(str(voice_path), "wb") as voice:
                voice.setnchannels(1)
                voice.setsampwidth(2)
                voice.setframerate(48000)
                voice.writeframes(b"\x00\x00" * 48000)

            mix_audio(voice_path, music_path, output_path, duration_s=2)

            with wave.open(str(output_path), "rb") as mixed:
                self.assertAlmostEqual(mixed.getnframes() / mixed.getframerate(), 2)


if __name__ == "__main__":
    unittest.main()
