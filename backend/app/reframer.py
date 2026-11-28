import os
import cv2
import numpy as np
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

from app.utils import FFMPEG_CMD, run_subprocess

logger = logging.getLogger("indoclip.reframer")

# Safe import for MediaPipe with OpenCV Haar Cascade fallback (for 100% Python 3.13+ compatibility)
mp = None
mp_face_detection = None
mp_face_mesh = None

try:
    import mediapipe as mp
    if hasattr(mp, "solutions"):
        mp_face_detection = mp.solutions.face_detection
        mp_face_mesh = mp.solutions.face_mesh
    else:
        from mediapipe.python.solutions import face_detection as mp_face_detection
        from mediapipe.python.solutions import face_mesh as mp_face_mesh
except Exception as e:
    logger.warning(f"MediaPipe tidak dimuat ({e}). Menggunakan OpenCV Haar Cascade built-in.")
    mp = None
    mp_face_detection = None
    mp_face_mesh = None

# Built-in OpenCV Haar Cascade fallback for face detection (zero extra dependency)
cv2_face_cascade = None
try:
    cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    cv2_face_cascade = cv2.CascadeClassifier(cascade_path)
    if cv2_face_cascade.empty():
        cv2_face_cascade = None
except Exception:
    cv2_face_cascade = None

class VideoReframer:
    """
    Tahap 5: Smart Multi-Mode Reframing (reframer.py)
    Mengubah video horizontal (16:9) menjadi vertikal (9:16) 1080x1920
    berdasarkan posisi wajah dan ekspresi bibir/mouth aspect ratio.
    """
    def __init__(self, sample_interval: int = 4):
        self.sample_interval = sample_interval  # Sampling tiap 4 frame (7.5 fps sampling) untuk kecepatan maksimal & pergerakan kamera halus
        self.target_w = 1080
        self.target_h = 1920
        self.aspect_ratio_9_16 = 9.0 / 16.0

    def compute_mar(self, landmarks, frame_w: int, frame_h: int) -> float:
        """
        Hitung Mouth Aspect Ratio (MAR) untuk deteksi pembicara aktif.
        Landmark bibir atas: 13, bibir bawah: 14, sudut bibir kiri: 61, sudut bibir kanan: 291.
        """
        try:
            top_lip = np.array([landmarks[13].x * frame_w, landmarks[13].y * frame_h])
            bottom_lip = np.array([landmarks[14].x * frame_w, landmarks[14].y * frame_h])
            left_corner = np.array([landmarks[61].x * frame_w, landmarks[61].y * frame_h])
            right_corner = np.array([landmarks[291].x * frame_w, landmarks[291].y * frame_h])
            
            vertical_dist = np.linalg.norm(top_lip - bottom_lip)
            horizontal_dist = np.linalg.norm(left_corner - right_corner) + 1e-6
            return float(vertical_dist / horizontal_dist)
        except Exception:
            return 0.0

    def analyze_faces_in_video(
        self,
        video_path: Path,
        max_duration: float = 65.0
    ) -> Dict[str, Any]:
        """
        Sampling frame video untuk mendeteksi jumlah wajah, posisi, dan pola gerak.
        """
        cap = cv2.VideoCapture(str(video_path))
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
        orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 1920)
        orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 1080)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if orig_w <= 0: orig_w = 1920
        if orig_h <= 0: orig_h = 1080
        
        if mp_face_detection is None and cv2_face_cascade is None:
            cap.release()
            return {
                "fps": fps,
                "orig_w": orig_w,
                "orig_h": orig_h,
                "total_frames": total_frames,
                "sampled_data": []
            }

        face_detector = mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5) if mp_face_detection else None
        
        sampled_data = []
        frame_idx = 0
        analysis_sample_interval = max(self.sample_interval, 5)  # Cukup sampling 5-6 kali per detik untuk analisis kategori video
        
        while cap.isOpened() and frame_idx < total_frames:
            ret, frame = cap.read()
            if not ret:
                break
                
            if frame_idx % analysis_sample_interval == 0:
                faces = []
                if face_detector:
                    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    results = face_detector.process(rgb_frame)
                    if results and results.detections:
                        for det in results.detections:
                            bbox = det.location_data.relative_bounding_box
                            xmin = int(bbox.xmin * orig_w)
                            ymin = int(bbox.ymin * orig_h)
                            w = int(bbox.width * orig_w)
                            h = int(bbox.height * orig_h)
                            area_ratio = (w * h) / (orig_w * orig_h + 1e-6)
                            cx = xmin + w // 2
                            cy = ymin + h // 2
                            faces.append({
                                "bbox": (xmin, ymin, w, h),
                                "center": (cx, cy),
                                "area_ratio": area_ratio
                            })
                elif cv2_face_cascade:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    dets = cv2_face_cascade.detectMultiScale(gray, 1.2, 4, minSize=(60, 60))
                    for (fx, fy, fw, fh) in dets:
                        area_ratio = (fw * fh) / (orig_w * orig_h + 1e-6)
                        faces.append({
                            "bbox": (int(fx), int(fy), int(fw), int(fh)),
                            "center": (int(fx + fw // 2), int(fy + fh // 2)),
                            "area_ratio": area_ratio
                        })
                sampled_data.append({"frame_idx": frame_idx, "faces": faces})
                
            frame_idx += 1
            
        cap.release()
        if face_detector:
            face_detector.close()
        
        return {
            "fps": fps,
            "orig_w": orig_w,
            "orig_h": orig_h,
            "total_frames": total_frames,
            "sampled_data": sampled_data
        }

    def auto_detect_category(self, analysis: Dict[str, Any]) -> str:
        """
        Mendeteksi otomatis apakah video berupa GAMING, PODCAST, atau SOLO.
        """
        sampled_data = analysis.get("sampled_data", [])
        orig_w = analysis.get("orig_w", 1920)
        orig_h = analysis.get("orig_h", 1080)
        
        if not sampled_data:
            return "SOLO"
            
        face_counts = [len(item["faces"]) for item in sampled_data]
        avg_faces = np.mean(face_counts) if face_counts else 1.0
        
        # Cek kriteria GAMING: 1 wajah kecil di sudut (< 8% area frame, xmin di pinggir)
        gaming_signals = 0
        for item in sampled_data:
            if len(item["faces"]) == 1:
                face = item["faces"][0]
                cx, cy = face["center"]
                area = face["area_ratio"]
                # Di sudut kiri atau kanan
                is_corner = (cx < 0.25 * orig_w or cx > 0.75 * orig_w)
                if area < 0.08 and is_corner:
                    gaming_signals += 1
                    
        if gaming_signals / max(1, len(sampled_data)) > 0.40:
            return "GAMING"
            
        if avg_faces >= 1.6:
            return "PODCAST"
            
        return "SOLO"

    def reframe_video(
        self,
        raw_video_path: Path,
        output_path: Path,
        category: str = "AUTO",
        relative_start: float = 0.0,
        duration: float = 30.0
    ) -> Path:
        """
        Memproses reframing video ke format 9:16 (1080x1920) sesuai mode.
        """
        analysis = self.analyze_faces_in_video(raw_video_path, max_duration=duration + 5.0)
        
        if category == "AUTO":
            resolved_category = self.auto_detect_category(analysis)
        else:
            resolved_category = category
            
        logger.info(f"Reframing {raw_video_path.name} using category mode: {resolved_category}")
        
        orig_w = analysis.get("orig_w", 1920)
        orig_h = analysis.get("orig_h", 1080)
        fps = float(analysis.get("fps", 30.0))
        
        # Hitung crop horizontal untuk aspek 9:16 dari tinggi video
        crop_w = int(orig_h * (9.0 / 16.0))
        if crop_w % 2 != 0:
            crop_w -= 1
            
        cap = cv2.VideoCapture(str(raw_video_path))
        
        # Potong posisi start ke relative_start jika ada
        start_frame = int(relative_start * fps)
        max_frames_to_read = int(duration * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        
        # Temporary video output tanpa audio
        temp_video_only = output_path.parent / f"{output_path.stem}_reframed_noaudio.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out_writer = cv2.VideoWriter(str(temp_video_only), fourcc, fps, (self.target_w, self.target_h))
        
        # Face Mesh & Detector diinisialisasi SEKALI di luar loop untuk kecepatan maksimal
        face_mesh = None
        face_detector = None
        face_detector_solo = None
        
        if resolved_category == "PODCAST" and mp_face_mesh and mp_face_detection:
            face_mesh = mp_face_mesh.FaceMesh(max_num_faces=4, refine_landmarks=True, min_detection_confidence=0.5)
            face_detector = mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)
        elif resolved_category == "SOLO" and mp_face_detection:
            face_detector_solo = mp_face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)
            
        # Smoothing & State variables
        smooth_cx = orig_w / 2.0
        ema_alpha = 0.08  # Pergerakan kamera halus
        last_speaker_switch_time = 0.0
        current_speaker_cx = orig_w / 2.0
        cached_podcast_boxes = []
        
        read_frames = 0
        try:
            while cap.isOpened() and read_frames < max_frames_to_read:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                current_time = read_frames / fps
                is_sample_frame = (read_frames % self.sample_interval == 0)
                
                if resolved_category == "GAMING":
                    # Mode GAMING: Facecam atas (1080x620) & Gameplay tengah bawah (1080x1300)
                    facecam_crop = frame[0:int(orig_h * 0.45), 0:int(orig_w * 0.35)]
                    if facecam_crop.size == 0:
                        facecam_crop = frame[0:orig_h, 0:int(orig_w * 0.3)]
                    facecam_resized = cv2.resize(facecam_crop, (self.target_w, 620))
                    
                    # Gameplay tengah
                    gameplay_crop = frame[0:orig_h, int(orig_w * 0.15) : int(orig_w * 0.85)]
                    gameplay_resized = cv2.resize(gameplay_crop, (self.target_w, 1300))
                    
                    final_canvas = np.vstack([facecam_resized, gameplay_resized])
                    
                elif resolved_category == "PODCAST":
                    # Mode PODCAST: Sampling deteksi wajah tiap sample_interval frame
                    if is_sample_frame and face_detector:
                        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        det_results = face_detector.process(rgb_frame)
                        
                        detected_boxes = []
                        if det_results and det_results.detections:
                            for det in det_results.detections:
                                bbox = det.location_data.relative_bounding_box
                                bx = int(bbox.xmin * orig_w)
                                by = int(bbox.ymin * orig_h)
                                bw = int(bbox.width * orig_w)
                                bh = int(bbox.height * orig_h)
                                detected_boxes.append((bx + bw // 2, by + bh // 2, bw, bh))
                        detected_boxes.sort(key=lambda b: b[0])
                        cached_podcast_boxes = detected_boxes
                        
                        # Active speaker tracking jika 1 atau 3+ wajah
                        if len(detected_boxes) != 2 and face_mesh:
                            mesh_results = face_mesh.process(rgb_frame)
                            if mesh_results and mesh_results.multi_face_landmarks:
                                best_mar = -1.0
                                best_cx = current_speaker_cx
                                for face_lm in mesh_results.multi_face_landmarks:
                                    mar = self.compute_mar(face_lm.landmark, orig_w, orig_h)
                                    cx_lm = int(face_lm.landmark[1].x * orig_w)
                                    if mar > best_mar:
                                        best_mar = mar
                                        best_cx = cx_lm
                                        
                                if (current_time - last_speaker_switch_time) >= 1.5 and best_mar > 0.08:
                                    if abs(best_cx - current_speaker_cx) > 80:
                                        current_speaker_cx = best_cx
                                        last_speaker_switch_time = current_time
                    
                    if len(cached_podcast_boxes) == 2:
                        # Tepat 2 Wajah -> Split-Screen Atas-Bawah (1080x960 masing-masing)
                        cx1, cy1, bw1, bh1 = cached_podcast_boxes[0]
                        cx2, cy2, bw2, bh2 = cached_podcast_boxes[1]
                        
                        half_w = int(orig_h * 0.5 * (1080.0 / 960.0) / 2)
                        x1_start = max(0, min(orig_w - 2 * half_w, cx1 - half_w))
                        crop1 = frame[0:orig_h, x1_start : x1_start + 2 * half_w]
                        top_screen = cv2.resize(crop1, (self.target_w, 960))
                        
                        x2_start = max(0, min(orig_w - 2 * half_w, cx2 - half_w))
                        crop2 = frame[0:orig_h, x2_start : x2_start + 2 * half_w]
                        bottom_screen = cv2.resize(crop2, (self.target_w, 960))
                        
                        final_canvas = np.vstack([top_screen, bottom_screen])
                    else:
                        smooth_cx = ema_alpha * current_speaker_cx + (1 - ema_alpha) * smooth_cx
                        x_start = int(max(0, min(orig_w - crop_w, smooth_cx - crop_w / 2)))
                        crop_region = frame[0:orig_h, x_start : x_start + crop_w]
                        final_canvas = cv2.resize(crop_region, (self.target_w, self.target_h))
                        
                else:
                    # Mode SOLO: Dynamic face tracking dengan EMA smoothing
                    if is_sample_frame:
                        if face_detector_solo:
                            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            results = face_detector_solo.process(rgb_frame)
                            if results and results.detections:
                                largest_area = 0
                                for det in results.detections:
                                    bbox = det.location_data.relative_bounding_box
                                    bw = int(bbox.width * orig_w)
                                    bh = int(bbox.height * orig_h)
                                    if bw * bh > largest_area:
                                        largest_area = bw * bh
                                        smooth_cx = ema_alpha * (int(bbox.xmin * orig_w) + bw // 2) + (1 - ema_alpha) * smooth_cx
                        elif cv2_face_cascade:
                            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                            dets = cv2_face_cascade.detectMultiScale(gray, 1.2, 4, minSize=(60, 60))
                            if len(dets) > 0:
                                largest = max(dets, key=lambda d: d[2] * d[3])
                                smooth_cx = ema_alpha * (largest[0] + largest[2] // 2) + (1 - ema_alpha) * smooth_cx
                        
                    x_start = int(max(0, min(orig_w - crop_w, smooth_cx - crop_w / 2)))
                    crop_region = frame[0:orig_h, x_start : x_start + crop_w]
                    final_canvas = cv2.resize(crop_region, (self.target_w, self.target_h))
                    
                out_writer.write(final_canvas)
                read_frames += 1
        finally:
            cap.release()
            out_writer.release()
            if face_mesh:
                try: face_mesh.close()
                except Exception: pass
            if face_detector:
                try: face_detector.close()
                except Exception: pass
            if face_detector_solo:
                try: face_detector_solo.close()
                except Exception: pass
            
        # Merge kembali audio dari file asli menggunakan FFmpeg
        logger.info(f"Muxing audio into reframed video {output_path.name}...")
        mux_cmd = [
            FFMPEG_CMD,
            "-y",
            "-i", str(temp_video_only),
            "-ss", f"{relative_start:.2f}",
            "-t", f"{duration:.2f}",
            "-i", str(raw_video_path),
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-map", "0:v:0",
            "-map", "1:a:0?",
            "-shortest",
            str(output_path)
        ]
        run_subprocess(mux_cmd)
        
        # Hapus temporary video
        if temp_video_only.exists():
            temp_video_only.unlink()
            
        return output_path

reframer = VideoReframer()
