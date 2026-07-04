import types
import unittest
from unittest.mock import patch

from services.tracking import metrics


class FakeSessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


class FakeProcessor:
    def __init__(self, latest_metrics):
        self.latest_metrics = latest_metrics
        self.exercise = None

    def set_exercise(self, exercise):
        self.exercise = exercise

    def get_latest_metrics(self):
        return self.latest_metrics


class MetricsSyncTest(unittest.TestCase):
    def setUp(self):
        self.session_state = FakeSessionState({
            "exercise_type": "Push-ups",
            "reps": 0,
            "reps_per_set": 10,
            "target_sets": 3,
            "last_saved_sets_completed": 0,
            "set_cycle_started_at": 100.0,
            "user_id": 7,
            "voice_pipeline": None,
        })
        self.fake_st = types.SimpleNamespace(session_state=self.session_state)

    def _context(self, latest_metrics):
        return types.SimpleNamespace(
            state=types.SimpleNamespace(playing=True),
            video_processor=FakeProcessor(latest_metrics),
        )

    def test_saves_each_completed_set_once(self):
        saved = []

        def save_exercise(*args):
            saved.append(args)

        with patch.object(metrics, "st", self.fake_st), patch.object(metrics, "time") as fake_time, patch.object(metrics, "add_exercise", save_exercise):
            fake_time.time.return_value = 140.0
            metrics.sync_metrics_update(
                self._context(
                    {
                        "reps": 20,
                        "pose_detected": True,
                        "elbow_angle": 165,
                        "body_alignment": "Straight",
                        "hip_status": "LEVEL",
                    }
                )
            )

        self.assertEqual(self.session_state["sets_completed"], 2)
        self.assertEqual(self.session_state["current_set_reps"], 0)
        self.assertEqual(self.session_state["last_saved_sets_completed"], 2)
        self.assertEqual(saved, [(7, "Push-ups", 20, 2, 40.0)])

    def test_workout_completes_when_target_sets_are_reached(self):
        with patch.object(metrics, "st", self.fake_st), patch.object(metrics, "time") as fake_time, patch.object(metrics, "add_exercise"):
            fake_time.time.return_value = 150.0
            metrics.sync_metrics_update(
                self._context(
                    {
                        "reps": 30,
                        "pose_detected": True,
                        "elbow_angle": 170,
                        "body_alignment": "Straight",
                        "hip_status": "LEVEL",
                    }
                )
            )

        self.assertTrue(self.session_state["workout_completed"])
        self.assertTrue(self.session_state["last_notified_workout_complete"])

    def test_no_pose_frame_keeps_existing_rep_count(self):
        self.session_state["reps"] = 12

        with patch.object(metrics, "st", self.fake_st), patch.object(metrics, "add_exercise"):
            metrics.sync_metrics_update(self._context({"pose_detected": False}))

        self.assertEqual(self.session_state["reps"], 12)


if __name__ == "__main__":
    unittest.main()
