"""
Verify the face gallery: every student folder should have at least
MIN_GALLERY_IMAGES images and every image should produce an embedding.

Run from the smart-attendance-system folder:
    python scripts/check_gallery.py

Exit code 0 = gallery healthy, 1 = at least one student needs re-capture.
Also warms the per-folder embedding cache as a side effect.
"""
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from services.face_recognition_service import (  # noqa: E402
    load_folder_embeddings, MIN_GALLERY_IMAGES, EMBEDDING_MODE
)

GALLERY_PATH = os.path.join(BASE_DIR, "datasets", "student_faces")


def main():
    if not os.path.isdir(GALLERY_PATH):
        print(f"Gallery folder not found: {GALLERY_PATH}")
        return 1

    print(f"Checking gallery: {GALLERY_PATH} (mode: {EMBEDDING_MODE})\n")
    problems = []

    for student in sorted(os.listdir(GALLERY_PATH)):
        student_path = os.path.join(GALLERY_PATH, student)
        if not os.path.isdir(student_path):
            continue

        embeddings = load_folder_embeddings(student_path)
        total = len(embeddings)
        valid = sum(1 for emb in embeddings.values() if emb is not None)
        failed = [name for name, emb in embeddings.items() if emb is None]

        status = "OK"
        if total == 0:
            status = "EMPTY FOLDER - delete it or register the student"
            problems.append(student)
        elif valid < MIN_GALLERY_IMAGES:
            status = f"NEEDS RE-CAPTURE (minimum {MIN_GALLERY_IMAGES} valid images)"
            problems.append(student)

        print(f"  {student}: {valid}/{total} images encode  [{status}]")
        for name in failed:
            print(f"      failed to encode: {name} (consider deleting it)")

    print()
    if problems:
        print(f"{len(problems)} student(s) need attention: {', '.join(problems)}")
        print("Fix via the register page with 'Re-capture photos' ticked.")
        return 1

    print("Gallery healthy: all students have enough valid images.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
