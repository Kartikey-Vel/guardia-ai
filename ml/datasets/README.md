# ML Datasets Directory

Store datasets here for training Guardia AI models.

## Directory Structure

```
datasets/
├── ntu_rgbd/              # NTU RGB+D skeleton dataset
│   ├── train/
│   │   ├── normal/
│   │   ├── fight_detected/
│   │   ├── fall_detected/
│   │   ├── running/
│   │   ├── trespassing/
│   │   ├── threatening_pose/
│   │   └── suspicious_movement/
│   ├── val/
│   └── test/
├── avenue/                # Avenue anomaly detection dataset
│   ├── train/
│   │   ├── normal/
│   │   └── anomaly/
│   ├── val/
│   └── train_annotations.json
├── ucsd_ped2/            # UCSD Pedestrian 2 dataset
│   ├── train/
│   └── test/
├── affectnet/            # AffectNet emotion dataset
│   ├── train/
│   │   ├── neutral/
│   │   ├── stress/
│   │   ├── aggression/
│   │   ├── sadness/
│   │   ├── fear/
│   │   └── anxiety/
│   ├── val/
│   └── train_annotations.csv
└── fer2013/              # FER2013 emotion dataset
    ├── train/
    └── test/
```

## Downloading Datasets

### NTU RGB+D 60

**Source**: [NTU RGB+D Dataset](https://rose1.ntu.edu.sg/dataset/actionRecognition/)

```bash
# Request access from the dataset website
# After approval, download skeleton data
wget <download_link>
unzip nturgb+d_skeletons_s001_to_s017.zip -d ntu_rgbd/
```

**Preprocessing**: Convert skeleton data to `.pkl` format with 17 COCO keypoints.

### Avenue Dataset

**Source**: [CUHK Avenue Dataset](http://www.cse.cuhk.edu.hk/leojia/projects/detectabnormal/dataset.html)

```bash
wget http://www.cse.cuhk.edu.hk/leojia/projects/detectabnormal/Avenue.zip
unzip Avenue.zip -d avenue/
```

**Format**: Video files (`.avi`) with frame-level annotations.

### UCSD Ped2

**Source**: [UCSD Anomaly Detection Dataset](http://www.svcl.ucsd.edu/projects/anomaly/dataset.htm)

```bash
wget http://www.svcl.ucsd.edu/projects/anomaly/UCSD_Anomaly_Dataset.tar.gz
tar -xzf UCSD_Anomaly_Dataset.tar.gz -C ucsd_ped2/
```

### AffectNet

**Source**: [AffectNet Dataset](http://mohammadmahoor.com/affectnet/)

**Note**: Requires registration and manual download due to licensing.

1. Register at the AffectNet website
2. Download training and validation sets
3. Extract to `affectnet/train/` and `affectnet/val/`
4. Organize images by emotion label

**Preprocessing**: Crop faces and blur backgrounds for privacy.

### FER2013

**Source**: [Kaggle FER2013](https://www.kaggle.com/datasets/msambare/fer2013)

```bash
pip install kaggle
kaggle datasets download -d msambare/fer2013
unzip fer2013.zip -d fer2013/
```

**Format**: CSV file with pixel values and emotion labels.

## Custom Data Collection

For production deployment, collect domain-specific data:

### Record from Cameras

```python
from utils.datasets import collect_camera_data

collect_camera_data(
    camera_url='rtsp://camera:554/stream',
    output_dir='custom_data/normal',
    duration_hours=24,
    fps=5
)
```

### Annotate Actions

Use annotation tools like [CVAT](https://github.com/openvinotoolkit/cvat) or [Label Studio](https://labelstud.io/).

### Generate Skeleton Data

```python
import cv2
import mediapipe as mp

# Extract skeleton keypoints from videos
mp_pose = mp.solutions.pose
pose = mp_pose.Pose()

for frame in video:
    results = pose.process(frame)
    landmarks = results.pose_landmarks
    # Save landmarks to .pkl
```

## Data Augmentation

Augmentation techniques are defined in training configs (`configs/*.yaml`):

- **Skeleton**: Rotation, scaling, shifting, noise
- **Video**: Flipping, cropping, brightness, contrast
- **Faces**: Rotation, flipping, brightness, contrast

## Dataset Statistics

| Dataset | Type | Size | Classes | Train Samples |
|---------|------|------|---------|---------------|
| NTU RGB+D | Skeleton | ~25 GB | 60 → 7 | ~40,000 |
| Avenue | Video | ~2 GB | 2 (binary) | 16 videos |
| UCSD Ped2 | Video | ~1 GB | 2 (binary) | 16 videos |
| AffectNet | Images | ~36 GB | 8 → 6 | ~280,000 |
| FER2013 | Images | ~300 MB | 7 → 6 | ~28,000 |

## Privacy Compliance

When using public datasets:

1. **Face Blurring**: Automatically blur faces in training data (except face crops for emotion)
2. **Background Removal**: Remove identifiable background elements
3. **Synthetic Data**: Consider using synthetic faces (e.g., StyleGAN-generated)
4. **Data Licensing**: Ensure compliance with dataset licenses for commercial use

## Notes

- This directory is in `.gitignore` to avoid committing large dataset files
- Store datasets on external storage (NAS, S3) for team sharing
- Use symlinks if datasets are stored elsewhere: `ln -s /mnt/datasets/ntu_rgbd ./ntu_rgbd`
