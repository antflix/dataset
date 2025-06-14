import os
import sys
from PIL import Image

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from dataset_generator import bbox_to_yolo, tile_image

def test_bbox_to_yolo():
    box = (0, 0, 100, 100)
    x_c, y_c, w, h = bbox_to_yolo(box, 200, 200)
    assert round(x_c, 2) == 0.25
    assert round(y_c, 2) == 0.25
    assert round(w, 2) == 0.5
    assert round(h, 2) == 0.5

def test_tile_image(tmp_path):
    img = Image.new('RGB', (100, 100))
    tiles = tile_image(img, tile_size=50)
    assert len(tiles) == 4
    # ensure tile sizes are correct
    for (_, tile) in tiles:
        w, h = tile.size
        assert w <= 50 and h <= 50
