import requests
from PIL import Image, ImageDraw

def get_bounding_boxes(image_path):
    url = "https://ml.antflix.net/predict"  # URL for the other Flask app
    files = {'image': open(image_path, 'rb')}

    try:
        response = requests.post(url, files=files)
        response.raise_for_status()
        bounding_boxes = response.json()
        return bounding_boxes
    except requests.RequestException as e:
        print(f"Error calling the prediction API: {e}")
        return None

import random
from PIL import Image, ImageDraw

import random
from PIL import Image, ImageDraw

def generate_random_color():
    # Generate a color that is not too close to white or black
    while True:
        color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
        # Check if the color is not too close to white (255, 255, 255) or black (0, 0, 0)
        if all(30 < c < 225 for c in color):  # Avoid very light or very dark colors
            return color

def draw_bounding_boxes(image_path, bounding_boxes):
    # Open the image
    image = Image.open(image_path)
    draw = ImageDraw.Draw(image)

    # Predefined colors to use first
    predefined_colors = [
        (255, 0, 0),    # Red
        (0, 0, 255),    # Blue
        (0, 255, 0),    # Green
        (255, 165, 0),  # Orange
        (128, 0, 128),  # Purple
        (255, 192, 203),# Pink
        (255, 255, 0)   # Yellow
    ]

    # Generate a color map for different object categories
    color_map = {}
    for obj in bounding_boxes:
        category_name = obj['ObjectPrediction']['category']['Category']['name']
        if category_name not in color_map:
            # Use predefined colors first, then generate random colors
            if len(color_map) < len(predefined_colors):
                color_map[category_name] = predefined_colors[len(color_map)]
            else:
                color_map[category_name] = generate_random_color()

    # Draw each bounding box with the assigned color
    for obj in bounding_boxes:
        bbox_str = obj['ObjectPrediction']['bbox']['BoundingBox']
        bbox = eval(bbox_str)  # Convert string to tuple
        category_name = obj['ObjectPrediction']['category']['Category']['name']
        color = color_map[category_name]  # Get the color for this category
        draw.rectangle(bbox, outline=color, width=3)
        draw.text((bbox[0], bbox[1]), category_name, fill=color)  # Optionally add the label

    # Save the annotated image
    annotated_image_path = image_path.replace(".png", "_annotated.png").replace(".jpg", "_annotated.jpg")
    image.save(annotated_image_path)
    return annotated_image_path

# Call draw_bounding_boxes using the bounding_boxes list directly
def count_objects(bounding_boxes):
    """
    Count the number of each category in the bounding boxes.
    """
    object_counts = {}
    for obj in bounding_boxes:
        category_name = obj['ObjectPrediction']['category']['Category']['name']
        if category_name not in object_counts:
            object_counts[category_name] = 0
        object_counts[category_name] += 1
    return object_counts

def format_object_counts(object_counts):
    """
    Format the object counts as a string to be prepended to the LLM input.
    """
    counts_str = "Objects found in the images:\n"
    for category, count in object_counts.items():
        counts_str += f"- {category}: {count}\n"
    return counts_str