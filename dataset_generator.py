# Utility script to generate dataset images and annotations from PDF blueprints
import os
import json
from typing import List, Tuple, Dict

from pdf2image import convert_from_path
from PIL import Image

from api_call import get_bounding_boxes


def pdf_to_images(pdf_path: str, dpi: int = 300) -> List[Tuple[str, Image.Image]]:
    """Convert each page of a PDF into PIL Images.

    Returns a list of tuples of (filename, Image).
    """
    images = convert_from_path(pdf_path, dpi=dpi)
    image_list = []
    base = os.path.splitext(os.path.basename(pdf_path))[0]
    for idx, img in enumerate(images):
        fname = f"{base}_page_{idx+1}.png"
        image_list.append((fname, img))
    return image_list


def save_full_images(image_list: List[Tuple[str, Image.Image]], out_dir: str) -> List[str]:
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for fname, img in image_list:
        path = os.path.join(out_dir, fname)
        img.save(path)
        paths.append(path)
    return paths


def parse_bbox(bbox_str: str) -> Tuple[float, float, float, float]:
    """Parse bounding box string '(x1, y1, x2, y2)'"""
    parts = bbox_str.strip("() ").split(",")
    return tuple(float(p) for p in parts)


def bbox_to_yolo(bbox: Tuple[float, float, float, float], img_w: int, img_h: int) -> Tuple[float, float, float, float]:
    x1, y1, x2, y2 = bbox
    w = x2 - x1
    h = y2 - y1
    x_c = x1 + w / 2
    y_c = y1 + h / 2
    return (x_c / img_w, y_c / img_h, w / img_w, h / img_h)


def save_crops_and_labels(image_path: str, bboxes: List[Dict], crop_dir: str, label_dir: str):
    os.makedirs(crop_dir, exist_ok=True)
    os.makedirs(label_dir, exist_ok=True)
    img = Image.open(image_path)
    img_w, img_h = img.size
    base = os.path.splitext(os.path.basename(image_path))[0]
    label_lines = []
    for idx, obj in enumerate(bboxes):
        bbox_str = obj['ObjectPrediction']['bbox']['BoundingBox']
        category_id = obj['ObjectPrediction']['category']['Category']['id']
        bbox = parse_bbox(bbox_str)
        x1, y1, x2, y2 = bbox
        crop = img.crop((x1, y1, x2, y2))
        crop_path = os.path.join(crop_dir, f"{base}_{idx}.png")
        crop.save(crop_path)
        yolo_box = bbox_to_yolo(bbox, img_w, img_h)
        label_lines.append(f"{category_id} {' '.join(f'{v:.6f}' for v in yolo_box)}")
    with open(os.path.join(label_dir, f"{base}.txt"), "w") as f:
        f.write("\n".join(label_lines))


def process_pdf(pdf_path: str, out_dir: str):
    images = pdf_to_images(pdf_path)
    full_dir = os.path.join(out_dir, "images")
    label_dir = os.path.join(out_dir, "labels")
    crop_dir = os.path.join(out_dir, "crops")
    saved_paths = save_full_images(images, full_dir)
    for img_path in saved_paths:
        bboxes = get_bounding_boxes(img_path)
        if bboxes:
            save_crops_and_labels(img_path, bboxes, crop_dir, label_dir)
        else:
            print(f"No bounding boxes for {img_path}")


def tile_image(image: Image.Image, tile_size: int = 1024, overlap: int = 0) -> List[Tuple[Tuple[int, int], Image.Image]]:
    """Split image into tiles with optional overlap."""
    tiles = []
    w, h = image.size
    step = tile_size - overlap
    for y in range(0, h, step):
        for x in range(0, w, step):
            box = (x, y, min(x + tile_size, w), min(y + tile_size, h))
            tiles.append(((x, y), image.crop(box)))
    return tiles


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate dataset from electrical blueprints")
    parser.add_argument("pdf", help="Path to PDF file")
    parser.add_argument("out", help="Output directory")
    args = parser.parse_args()
    process_pdf(args.pdf, args.out)
