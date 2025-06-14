install deps with "pip install -r requirements.txt"
must have OPENAI_API_KEY and ROBOFLOW_API_KEY set as enviornmental variables

Here is an example of what is returned from the api call in api_call.py:
```
json

{
  "ObjectPrediction": {
    "bbox": {
      "BoundingBox": "(2213.1000000000004, 935.925, 2257.95, 980.775)",
      "w": 44.849999999999454,
      "h": 44.85000000000002
    },
    "score": {
      "PredictionScore": 0.8940939903259277
    },
    "category": {
      "Category": {
        "id": 11,
        "name": "Exit Sign"
      }
    }
  }
}

```


Here is an example of what is returned from the api call in inference.py:

```
json


[
  {
    "dynamic_crop": [
      {
        "type": "base64",
        "value": "/9j/4AAQSkZJRgAB...oCjpklFAH/9k=",
        "video_metadata": {
          "video_identifier": "4ce5e66a-b235-4d8e-9efd-75edff9ea406",
          "frame_number": 0,
          "frame_timestamp": "2025-06-14T13:34:42.514488",
          "fps": 30,
          "measured_fps": null,
          "comes_from_video_file": null
        }
      }
    ],
    "model_predictions": {
      "inference_id": "62bea704-827a-403e-b5d1-f56e56017354",
      "predictions": {
        "image": {
          "width": 2048,
          "height": 1365
        },
        "predictions": [
          {
            "width": 685,
            "height": 357,
            "x": 859.5,
            "y": 250.5,
            "confidence": 0.7081630229949951,
            "class_id": 0,
            "points": [
              {
                "x": 1056,
                "y": 140
              },
              {
                "x": 1052,
                "y": 144
              },
              ...
              ...
              ...
              {
                "x": 1120,
                "y": 140
              }
            ],
            "class": "lightprint",
            "detection_id": "4ce5e66a-b235-4d8e-9efd-75edff9ea406",
            "parent_id": "image"
          }
        ]
      }
    }
  }
]


```
