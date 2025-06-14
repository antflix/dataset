import os
from shutil import copy2
from PIL import Image

DATASET_DIR = "dataset_output"


def _ensure_dirs():
    subdirs = [
        os.path.join(DATASET_DIR, "images", "full"),
        os.path.join(DATASET_DIR, "images", "crops"),
        os.path.join(DATASET_DIR, "labels", "full"),
        os.path.join(DATASET_DIR, "labels", "crops"),
    ]
    for d in subdirs:
        os.makedirs(d, exist_ok=True)


def save_full_image(image_path: str) -> str:
    """Copy the full-size page image to the dataset directory."""
    _ensure_dirs()
    dest = os.path.join(DATASET_DIR, "images", "full", os.path.basename(image_path))
    copy2(image_path, dest)
    return dest


def _yolo_line(class_id: int, x1: float, y1: float, x2: float, y2: float, img_w: int, img_h: int) -> str:
    x_center = ((x1 + x2) / 2) / img_w
    y_center = ((y1 + y2) / 2) / img_h
    w = (x2 - x1) / img_w
    h = (y2 - y1) / img_h
    return f"{class_id} {x_center} {y_center} {w} {h}"


def _write_lines(path: str, lines, mode: str = "w"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, mode) as f:
        for line in lines:
            f.write(line + "\n")


def save_crop_and_labels(full_image_path: str, crop_bbox, crop_path: str, annotations: list):
    """Save cropped image and annotation labels in YOLO format.

    Parameters
    ----------
    full_image_path : str
        Path to the original page image.
    crop_bbox : tuple
        (x1, y1, x2, y2) coordinates of the crop on the full image.
    crop_path : str
        Path to the cropped image file.
    annotations : list
        List of annotation objects returned by the prediction API for this crop.
    """
    _ensure_dirs()
    # copy crop image
    crop_dest = os.path.join(DATASET_DIR, "images", "crops", os.path.basename(crop_path))
    copy2(crop_path, crop_dest)

    with Image.open(full_image_path) as im_full:
        full_w, full_h = im_full.size
    with Image.open(crop_path) as im_crop:
        crop_w, crop_h = im_crop.size

    crop_label_path = os.path.join(
        DATASET_DIR,
        "labels",
        "crops",
        os.path.splitext(os.path.basename(crop_path))[0] + ".txt",
    )
    full_label_path = os.path.join(
        DATASET_DIR,
        "labels",
        "full",
        os.path.splitext(os.path.basename(full_image_path))[0] + ".txt",
    )

    crop_lines = []
    full_lines = []

    for obj in annotations:
        bbox_str = obj["ObjectPrediction"]["bbox"]["BoundingBox"]
        x1_rel, y1_rel, x2_rel, y2_rel = eval(bbox_str)
        class_id = obj["ObjectPrediction"]["category"]["Category"]["id"]

        # YOLO line for crop image
        crop_lines.append(
            _yolo_line(class_id, x1_rel, y1_rel, x2_rel, y2_rel, crop_w, crop_h)
        )

        # Convert bbox to full image coordinates
        x1_full = crop_bbox[0] + x1_rel
        y1_full = crop_bbox[1] + y1_rel
        x2_full = crop_bbox[0] + x2_rel
        y2_full = crop_bbox[1] + y2_rel
        full_lines.append(
            _yolo_line(class_id, x1_full, y1_full, x2_full, y2_full, full_w, full_h)
        )

    _write_lines(crop_label_path, crop_lines, mode="w")
    _write_lines(full_label_path, full_lines, mode="a")
    return crop_dest
