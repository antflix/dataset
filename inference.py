from inference_sdk import InferenceHTTPClient
import base64
from PIL import Image
import io
import os
from dataset_utils import save_full_image
import re


def _sanitize(label: str) -> str:
    """Convert label to a filesystem-safe string."""
    return re.sub(r"[^A-Za-z0-9_-]+", "_", label).strip("_")


def run_inference_and_save_images(image_paths):
    from app import app
    client = InferenceHTTPClient(
        api_url="https://detect.roboflow.com",
        api_key=os.getenv("ROBOFLOW_API_KEY")
    )
    
    output_info = {}
    for keyword, image_path in image_paths.items():
        safe_keyword = _sanitize(keyword)
        # Construct the full path and check if the image file exists
        full_image_path = os.path.join(app.config['IMAGES_FOLDER'], image_path)
        if not os.path.isfile(full_image_path):
            print(f"Image file does not exist: {full_image_path}")
            continue
        
        print(f"Running inference on image: {full_image_path}")
        save_full_image(full_image_path)
        
        # Try sending the image path to the inference server
        try:
            # Pass the image path as a string in the request
            result = client.run_workflow(
                workspace_name="workspace-lf7bo",
                workflow_id="custom-workflow",
                images={
                    "image": full_image_path  # Provide the image path instead of the file object
                }
            )
            print(f"Inference result for {keyword}: dynamic_crop length = {len(result[0].get('dynamic_crop', []))}")

            # Check if the result contains 'dynamic_crop' items
            crops = result[0].get('dynamic_crop', [])
            predictions = result[0].get('model_predictions', {}).get('predictions', {}).get('predictions', [])
            if crops:
                for idx, crop_info in enumerate(crops):
                    if isinstance(crop_info, str):
                        try:
                            image_data = base64.b64decode(crop_info)
                            image = Image.open(io.BytesIO(image_data))
                            output_filename = f"{safe_keyword}_output_crop_{idx}.jpg"

                            output_path = os.path.join(app.config['IMAGES_FOLDER'], output_filename)
                            image.save(output_path)
                            crop_bbox = None
                            if idx < len(predictions):
                                p = predictions[idx]
                                crop_bbox = (
                                    p['x'] - p['width'] / 2,
                                    p['y'] - p['height'] / 2,
                                    p['x'] + p['width'] / 2,
                                    p['y'] + p['height'] / 2,
                                )
                            output_info[f"{keyword} Crop {idx}"] = {
                                'filename': output_filename,
                                'bbox': crop_bbox,
                                'source': image_path,
                            }
                            print(f"Saved cropped image {idx} for {keyword} successfully at {output_path}.")
                        except Exception as e:
                            print(f"Failed to process crop_info at index {idx} for {keyword}: {e}")
            else:
                print(f"No valid 'dynamic_crop' data found for {keyword} in the result.")
        
        except Exception as e:
            print(f"Failed to connect to the inference server: {e}")

    return output_info
