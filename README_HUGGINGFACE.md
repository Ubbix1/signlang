# Using Hugging Face Datasets with SignAI

This guide explains how to integrate Hugging Face's sign language dataset with the SignAI project and add hand landmark visualization to your camera feed.

## Setup

1. **Install required packages**

   Update your environment to include the Hugging Face dataset packages:

   ```bash
   pip install -r requirements.txt
   ```

2. **Configure the application**

   The application is pre-configured to use the "NAM27/sign-language" dataset from Hugging Face. If you want to use a different dataset, you can change it in the configuration.

## Loading the Dataset

You can load the dataset in two ways:

### 1. API Endpoint

Once the application is running, use the API endpoint to load the dataset:

```
POST /api/hf/load
Content-Type: application/json

{
  "dataset_name": "NAM27/sign-language" 
}
```

### 2. Configuration

Set the following in your .env file:

```
HF_DATASET_NAME=NAM27/sign-language
HF_CACHE_DIR=./data/huggingface
HF_AUTOLOAD=True
```

## Using the Example Script

We've included an example script to demonstrate how to:
1. Load the dataset
2. Explore its structure
3. Visualize samples
4. Train a model

Run the example:

```bash
python examples/huggingface_example.py
```

To train a model from the dataset, add the `--train` flag:

```bash
python examples/huggingface_example.py --train
```

## Hand Landmark Visualization

The project now includes enhanced hand landmark visualization. When you use the sign language recognition functionality, you can see:

1. Colored landmarks for different fingers
2. Connections between landmarks
3. Landmark indices
4. Confidence scores

To use the enhanced visualization, send requests to:

```
POST /api/process/with_landmarks
Content-Type: application/json

{
  "image": "base64_encoded_image"
}
```

The response will include a `debug_image` field with the visualization.

## Dataset Structure

The "NAM27/sign-language" dataset contains:
- Images with hand gestures
- Labels corresponding to sign language gestures
- Training and test splits

## API Endpoints

The following endpoints are available:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/hf/load` | POST | Load the Hugging Face dataset |
| `/api/hf/info` | GET | Get information about the loaded dataset |
| `/api/process/with_landmarks` | POST | Process an image and return prediction with landmarks |

## Troubleshooting

If you encounter issues:

1. **Dataset fails to load**
   - Check your internet connection
   - Verify the dataset name is correct
   - Ensure you have sufficient disk space

2. **Visualization issues**
   - Make sure MediaPipe is installed correctly
   - Check that the image format is supported

3. **Model training errors**
   - Verify TensorFlow is installed correctly
   - Check that the dataset structure matches the expected format

For more help, check the application logs or submit an issue. 