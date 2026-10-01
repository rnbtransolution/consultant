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
