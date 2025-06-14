from inference_sdk import InferenceHTTPClient
import base64
from PIL import Image
import io
import os
import os
from inference_sdk import InferenceHTTPClient

def run_inference_and_save_images(image_paths):
    from app import app
    client = InferenceHTTPClient(
        api_url="https://detect.roboflow.com",
        api_key=os.getenv("ROBOFLOW_API_KEY")
    )
    
    output_image_paths = {}
    for keyword, image_path in image_paths.items():
        # Construct the full path and check if the image file exists
        full_image_path = os.path.join(app.config['IMAGES_FOLDER'], image_path)
        if not os.path.isfile(full_image_path):
            print(f"Image file does not exist: {full_image_path}")
            continue
        
        print(f"Running inference on image: {full_image_path}")
        
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
            if 'dynamic_crop' in result[0] and isinstance(result[0]['dynamic_crop'], list) and result[0]['dynamic_crop']:
                for idx, crop_info in enumerate(result[0]['dynamic_crop']):
                    if isinstance(crop_info, str):
                        try:
                            # Decode the base64 string
                            image_data = base64.b64decode(crop_info)
                            # Convert the decoded bytes to an image
                            image = Image.open(io.BytesIO(image_data))
                            # Save the image to a file
                            output_filename = f"{keyword}_output_crop_{idx}.jpg"
                            output_path = os.path.join(app.config['IMAGES_FOLDER'], output_filename)
                            image.save(output_path)
                            # Store the output path for rendering
                            output_image_paths[f"{keyword} Crop {idx}"] = output_filename
                            print(f"Saved cropped image {idx} for {keyword} successfully at {output_path}.")
                        except Exception as e:
                            print(f"Failed to process crop_info at index {idx} for {keyword}: {e}")
            else:
                print(f"No valid 'dynamic_crop' data found for {keyword} in the result.")
        
        except Exception as e:
            print(f"Failed to connect to the inference server: {e}")

    return output_image_paths