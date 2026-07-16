import logging
import time
from collections import deque
from pathlib import Path

import numpy as np

from my_app.camera.face_util.insightface_engine import InsightFaceEngine
from my_app.camera.liveness_gate import LivenessGate
from my_app.camera.passive_pad import PassivePad
from my_app.service import face_service

logger = logging.getLogger(__name__)


class FaceAuthenticator:
    """
    複数顔、IR、PAD、連続判定をまとめて処理する
    """

    def __init__(self, face_dir, config):
        self.face_dir = Path(face_dir)
        self.config = dict(config)

        det_size = tuple(config.get("insightface_det_size", [256, 256]))

        self.engine = InsightFaceEngine(det_size=det_size)
        self.liveness = LivenessGate(config)
        self.passive_pad = PassivePad(threshold = config["pad_threshold"])

        self.similarity_threshold = float(config["similarity_threshold"])
        self.margin_threshold = float(config["margin_threshold"])
        self.required_success_frames = int(config["required_success_frames"])
        self.unlock_cooldown_sec = float(config["unlock_cooldown_sec"])
        self.global_unlock_cooldown_sec = float(config.get("global_unlock_cooldown_sec", 2.0))

        self.max_faces = int(config.get("max_faces", 4))
        self.match_top_k = int(config.get("match_top_k", 2))
        self.face_state_timeout_sec = float(config.get("face_state_timeout_sec", 1.0))
        self.min_track_iou = float(config.get("min_track_iou", 0.1))
        self.auth_min_det_score = float(config.get("auth_min_det_score", 0.6))
        self.auth_min_face_px = int(config.get("auth_min_face_px", 70))

        self.pad_window_size = int(config["pad_window_size"])
        self.pad_required_passes = int(config["pad_required_passes"])

        if self.pad_required_passes > self.pad_window_size:
            raise ValueError("pad_required_passesはpad_window_size以下にして😡")

        self.template_records = []
        self.template_matrix = np.empty((0, 0), dtype=np.float32)
        self.user_template_indices = {}
        self.user_names = {}

        self.face_states = {}
        self.last_unlock_by_user = {}
        self.last_global_unlock_at = 0.0

        self.reload_database_embeddings()

    @staticmethod
    def _normalize_embedding(embedding):
        vector = np.asarray(embedding, dtype = np.float32).reshape(-1)

        norm = float(np.linalg.norm(vector))

        if norm <= 0:
            raise ValueError("顔特徴量のノルムが0")

        return (vector / norm).astype(np.float32)

    def reload_database_embeddings(self):
        templates = face_service.load_authentication_templates()
        records = []

        for template in templates:
            try:
                embedding = self._normalize_embedding(template["embedding"])
            except ValueError:
                logger.warning("無効な顔特徴量です face_id=%s", template.get("face_id"))
                continue

            records.append({
                "face_id": template["face_id"],
                "user_id": template["user_id"],
                "name": template["name"],
                "embedding": embedding
            })

        self.template_records = records
        self.user_template_indices = {}
        self.user_names = {}

        for index, record in enumerate(records):
            user_id = record["user_id"]

            self.user_template_indices.setdefault(user_id, []).append(index)

            self.user_names[user_id] = record["name"]

        if records:
            self.template_matrix = np.stack([record["embedding"] for record in records]).astype(np.float32)
        else:
            self.template_matrix = np.empty((0, 0), dtype=np.float32)

        self.face_states.clear()

        print(f"顔特徴量読込 人数={len(self.user_names)} テンプレート数={len(records)}")

    def _match(self, embedding):
        if self.template_matrix.size == 0:
            return {
                "accepted": False,
                "user_id": None,
                "name": None,
                "score": 0.0,
                "margin": 0.0
            }

        embedding = self._normalize_embedding(embedding)

        template_scores = (self.template_matrix @ embedding)

        user_scores = []

        for user_id, indices in (self.user_template_indices.items()):
            scores = template_scores[np.asarray(indices, dtype=np.int32)]

            top_count = min(max(1, self.match_top_k), len(scores))

            score = float(np.mean(np.sort(scores)[-top_count:]))

            user_scores.append({
                "user_id": user_id,
                "name": self.user_names[user_id],
                "score": score,
                "best_template_score": float(
                    np.max(scores)
                ),
            })

        user_scores.sort(key=lambda item: item["score"], reverse=True)

        best = user_scores[0]
        second_score = (user_scores[1]["score"] if len(user_scores) > 1 else 0.0)
        margin = best["score"] - second_score

        accepted = (
            best["score"] >= self.similarity_threshold
            and (
                len(user_scores) == 1
                or margin >= self.margin_threshold
            )
        )

        return {
            "accepted": accepted,
            "user_id": best["user_id"],
            "name": best["name"],
            "score": best["score"],
            "margin": margin,
            "best_template_score": (
                best["best_template_score"]
            ),
        }

    def _face_is_usable(self, face_info):
        bbox = face_info["bbox"]
        width = float(bbox[2] - bbox[0])
        height = float(bbox[3] - bbox[1])

        if (face_info["det_score"] < self.auth_min_det_score):
            return False, "low_detection_score"

        if min(width, height) < self.auth_min_face_px:
            return False, "face_too_small"

        return True, "ok"

    @staticmethod
    def _bbox_iou(first, second):
        first = np.asarray(first, dtype=np.float32)
        second = np.asarray(second, dtype=np.float32)

        x1 = max(first[0], second[0])
        y1 = max(first[1], second[1])
        x2 = min(first[2], second[2])
        y2 = min(first[3], second[3])

        intersection = (max(0.0, x2 - x1) * max(0.0, y2 - y1))

        first_area = (max(0.0, first[2] - first[0]) * max(0.0, first[3] - first[1]))
        second_area = (max(0.0, second[2] - second[0]) * max(0.0, second[3] - second[1]))

        union = first_area + second_area - intersection

        if union <= 0:
            return 0.0

        return float(intersection / union)

    def _new_state(self, bbox, now):
        return {
            "count": 0,
            "pad_results": deque(maxlen=self.pad_window_size),
            "last_seen_at": now,
            "bbox": np.asarray(bbox, dtype=np.float32)
        }

    def _get_state(self, user_id, bbox, now):
        state = self.face_states.get(user_id)

        expired = (state is None or now - state["last_seen_at"] > self.face_state_timeout_sec)

        moved = (state is not None and self._bbox_iou(state["bbox"], bbox) < self.min_track_iou)

        if expired or moved:
            state = self._new_state(bbox, now)
            self.face_states[user_id] = state

        state["last_seen_at"] = now
        state["bbox"] = np.asarray(bbox, dtype=np.float32)

        return state

    def _expire_states(self, now):
        expired_ids = [user_id for user_id, state in self.face_states.items() if now - state["last_seen_at"] > self.face_state_timeout_sec]

        for user_id in expired_ids:
            self.face_states.pop(user_id, None)

    def authenticate(
        self,
        rgb_frame,
        ir_frame,
        rgb_timestamp=None,
        ir_timestamp=None
    ):
        now = time.monotonic()
        self._expire_states(now)

        frame_gap_ms = None

        if (rgb_timestamp is not None and ir_timestamp is not None):
            frame_gap_ms = abs(rgb_timestamp - ir_timestamp) * 1000.0

        faces = self.engine.extract_many(rgb_frame)[:self.max_faces]

        if not faces:
            return None, {
                "reason": "no_face",
                "face_count": 0,
                "faces": [],
                "frame_gap_ms": frame_gap_ms
            }

        results = []
        best_face_by_user = {}

        for face_index, face_info in enumerate(faces):
            usable, quality_reason = (self._face_is_usable(face_info))

            if not usable:
                results.append({
                    "reason": quality_reason,
                    "face_index": face_index,
                    "bbox": face_info["bbox"].tolist(),
                    "score": 0.0
                })
                continue

            match = self._match(face_info["embedding"])

            if not match["accepted"]:
                results.append({
                    "reason": "not_matched",
                    "face_index": face_index,
                    "bbox": face_info["bbox"].tolist(),
                    "user_id": match["user_id"],
                    "name": match["name"],
                    "score": match["score"],
                    "margin": match["margin"]
                })
                continue

            user_id = match["user_id"]
            previous = best_face_by_user.get(user_id)

            if (previous is None or match["score"] > previous["match"]["score"]):
                best_face_by_user[user_id] = {"face_index": face_index, "face_info": face_info, "match": match}

        authenticated_results = []

        for user_id, candidate in (best_face_by_user.items()):
            face_index = candidate["face_index"]
            face_info = candidate["face_info"]
            match = candidate["match"]

            ir_ok, ir_information = (
                self.liveness.check_ir_response(ir_frame = ir_frame, bbox = face_info["bbox"], rgb_shape = rgb_frame.shape,))

            if not ir_ok:
                self.face_states.pop(user_id, None)

                results.append({
                    "reason": ir_information["reason"],
                    "face_index": face_index,
                    "bbox": face_info["bbox"].tolist(),
                    "user_id": user_id,
                    "name": match["name"],
                    "score": match["score"],
                    "margin": match["margin"],
                    "ir": ir_information
                })
                continue

            try:
                is_live, pad_information = (self.passive_pad.check(rgb_frame, face_info["bbox"]))
            except Exception:
                logger.exception("PADモデル推論エラー")
                self.face_states.pop(user_id, None)

                results.append({
                    "reason": "pad_error",
                    "face_index": face_index,
                    "user_id": user_id,
                    "name": match["name"],
                    "score": match["score"]
                })
                continue

            state = self._get_state(user_id, face_info["bbox"], now)

            state["count"] += 1
            state["pad_results"].append(bool(is_live))

            pad_pass_count = sum(state["pad_results"])
            required_count = max(self.required_success_frames, self.pad_window_size)

            result = {
                "reason": "need_more_frames",
                "face_index": face_index,
                "bbox": face_info["bbox"].tolist(),
                "user_id": user_id,
                "name": match["name"],
                "score": match["score"],
                "margin": match["margin"],
                "count": state["count"],
                "required": required_count,
                "pad_score": (
                    pad_information["live_score"]
                ),
                "pad_pass_count": pad_pass_count,
                "pad_required_passes": (
                    self.pad_required_passes
                ),
                "ir": ir_information
            }

            if (len(state["pad_results"]) < self.pad_window_size or state["count"] < self.required_success_frames):
                results.append(result)
                continue

            if (pad_pass_count < self.pad_required_passes):
                result["reason"] = "spoof_detected"
                results.append(result)
                self.face_states.pop(user_id, None)
                continue

            last_user_unlock = (self.last_unlock_by_user.get(user_id, 0.0,))

            user_cooldown = (now - last_user_unlock < self.unlock_cooldown_sec)
            global_cooldown = (now - self.last_global_unlock_at< self.global_unlock_cooldown_sec)

            if user_cooldown or global_cooldown:
                result["reason"] = "cooldown"
                results.append(result)
                self.face_states.pop(user_id, None)
                continue

            result["reason"] = "authenticated"
            results.append(result)
            authenticated_results.append(result)

        if authenticated_results:
            winner = max(authenticated_results, key=lambda item: item["score"])

            self.last_unlock_by_user[winner["user_id"]] = now
            self.last_global_unlock_at = now
            self.face_states.clear()

            information = dict(winner)
            information["faces"] = results
            information["face_count"] = len(faces)
            information["frame_gap_ms"] = frame_gap_ms

            return winner["name"], information

        if results:
            best_result = max(
                results,
                key = lambda item: item.get(
                    "score",
                    -1.0
                )
            )

            information = dict(best_result)
            information["faces"] = results
            information["face_count"] = len(faces)
            information["frame_gap_ms"] = frame_gap_ms

            return None, information

        return None, {
            "reason": "no_candidate",
            "face_count": len(faces),
            "faces": [],
            "frame_gap_ms": frame_gap_ms
        }

    def _reset(self):
        self.face_states.clear()