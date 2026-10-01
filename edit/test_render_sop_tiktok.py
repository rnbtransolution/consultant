import unittest

from edit.render_sop_tiktok import NARRATION_TH, SCENES, total_duration_s, validate_timeline


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


if __name__ == "__main__":
    unittest.main()
