import io
import unittest
import subprocess
import tempfile
import wave
from pathlib import Path
from unittest.mock import Mock, patch

from PIL import Image

from edit.render_sop_tiktok import (
    DEEP_GREEN,
    FRAME_HEIGHT,
    FRAME_WIDTH,
    LAYOUT_BOXES,
    NARRATION_TH,
    SCENES,
    FPS,
    create_instrumental,
    mix_audio,
    preflight_audio_tools,
    preflight_visual_assets,
    render_audio,
    render_frame,
    render_video,
    scene_index_at,
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

    def test_narration_uses_male_polite_particles_for_selected_voice(self):
        self.assertNotIn("คะ?", NARRATION_TH)
        self.assertNotIn("ค่ะ", NARRATION_TH)
        self.assertTrue(NARRATION_TH.endswith("ครับ"))

    def test_scene_narration_has_one_line_per_storyboard_scene(self):
        from edit.render_sop_tiktok import NARRATION_BY_SCENE

        self.assertEqual(len(NARRATION_BY_SCENE), len(SCENES))
        self.assertTrue(all(line.strip() for line in NARRATION_BY_SCENE))
        self.assertEqual(NARRATION_BY_SCENE[0], SCENES[0]["th"])
        self.assertIn("นัดหมายปรึกษาฟรี", NARRATION_BY_SCENE[-1])

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

    def test_narration_audio_starts_at_each_matching_scene_boundary(self):
        from edit.render_sop_tiktok import assemble_narration_by_scene

        with tempfile.TemporaryDirectory() as temporary_dir:
            directory = Path(temporary_dir)
            clips = []
            for index in range(len(SCENES)):
                clip_path = directory / f"clip-{index}.wav"
                with wave.open(str(clip_path), "wb") as clip:
                    clip.setnchannels(1)
                    clip.setsampwidth(2)
                    clip.setframerate(48000)
                    clip.writeframes(b"\x01\x00" * 4800)
                clips.append(clip_path)
            output_path = assemble_narration_by_scene(clips, directory / "voice.wav")

            with wave.open(str(output_path), "rb") as voice:
                frames = voice.readframes(voice.getnframes())
                frame_bytes = voice.getsampwidth() * voice.getnchannels()
                self.assertAlmostEqual(voice.getnframes() / voice.getframerate(), 24.1)
            self.assertEqual(frames[round(2.9 * 48000) * frame_bytes :][:2], b"\x00\x00")
            self.assertEqual(frames[3 * 48000 * frame_bytes :][:2], b"\x01\x00")
            self.assertEqual(frames[24 * 48000 * frame_bytes :][:2], b"\x01\x00")


class VisualTests(unittest.TestCase):
    def test_frame_uses_vertical_rgb_canvas_and_brand_background(self):
        frame = render_frame(1)

        self.assertEqual(frame.size, (FRAME_WIDTH, FRAME_HEIGHT))
        self.assertEqual(frame.mode, "RGB")
        self.assertEqual(frame.getpixel((1, 500)), DEEP_GREEN)
        self.assertEqual(frame.getpixel((1, FRAME_HEIGHT - 2)), DEEP_GREEN)

    def test_scene_selection_switches_on_each_timeline_boundary(self):
        boundaries = [scene["start_s"] for scene in SCENES]
        self.assertEqual([scene_index_at(time_s) for time_s in boundaries], list(range(6)))
        self.assertEqual(scene_index_at(total_duration_s()), 5)

    def test_layout_boxes_respect_tiktok_safe_zones(self):
        for name, (left, top, right, bottom) in LAYOUT_BOXES.items():
            with self.subTest(name=name):
                self.assertGreaterEqual(left, 0)
                self.assertGreaterEqual(top, 260)
                self.assertLessEqual(right, 860)
                self.assertLessEqual(bottom, 1380)
        self.assertGreaterEqual(LAYOUT_BOXES["header"][1], 270)
        self.assertGreaterEqual(LAYOUT_BOXES["captions"][1], 1200)
        self.assertLessEqual(LAYOUT_BOXES["captions"][3], 1370)

    @patch(
        "edit.render_sop_tiktok.SUITE_IMAGE_PATH",
        Path("/tmp/missing-sop-suite-mockup.jpg"),
    )
    def test_visual_preflight_reports_a_missing_required_mockup(self):
        with self.assertRaisesRegex(RuntimeError, "missing-sop-suite-mockup"):
            preflight_visual_assets()

    @patch(
        "edit.render_sop_tiktok.TITLE_FONT_PATH",
        Path("/tmp/missing-thai-title-font.ttf"),
    )
    def test_visual_preflight_reports_a_missing_required_font(self):
        with self.assertRaisesRegex(RuntimeError, "missing-thai-title-font"):
            preflight_visual_assets()

    def test_failed_ffmpeg_render_leaves_no_final_or_temporary_video(self):
        with tempfile.TemporaryDirectory() as temporary_dir:
            directory = Path(temporary_dir)
            output_path = directory / "final.mp4"
            fake_process = Mock()
            fake_process.stdin = io.BytesIO()
            fake_process.stderr = io.BytesIO(b"encode failed")
            fake_process.wait.return_value = 1
            fake_process.poll.return_value = 1
            fake_audio = directory / "audio.wav"

            with (
                patch("edit.render_sop_tiktok.FRAME_WIDTH", 4),
                patch("edit.render_sop_tiktok.FRAME_HEIGHT", 4),
                patch("edit.render_sop_tiktok.FPS", 1),
                patch("edit.render_sop_tiktok.preflight_visual_assets"),
                patch("edit.render_sop_tiktok.preflight_audio_tools"),
                patch("edit.render_sop_tiktok.render_audio", return_value=(fake_audio, fake_audio)),
                patch("edit.render_sop_tiktok.mix_audio", return_value=fake_audio),
                patch("edit.render_sop_tiktok.render_frame", return_value=Image.new("RGB", (4, 4))),
                patch("edit.render_sop_tiktok.subprocess.Popen", return_value=fake_process),
            ):
                with self.assertRaisesRegex(RuntimeError, "encode failed"):
                    render_video(output_path)

            self.assertFalse(output_path.exists())
            self.assertEqual(list(directory.glob(".final.*.tmp.mp4")), [])


if __name__ == "__main__":
    unittest.main()
