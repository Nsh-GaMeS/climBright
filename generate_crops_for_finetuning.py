"""
Generate classifier training crops from raw images using YOLO detector.
This creates a dataset for fine-tuning the ConvNeXt classifier on detector-generated crops.
"""
import os
import argparse
import shutil
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
from ultralytics import YOLO
from tqdm import tqdm

# =========================
# CONFIGURATION
# =========================
YOLO_MODEL = "runs/detect/train2/weights/best.pt"
YOLO_CONF_THRESHOLD = 0.3  # Higher threshold for cleaner training data
BOX_PADDING = 0.15
CLASS_NAMES = ["jug", "crimp", "pinch", "sloper", "pocket", "volume"]
OUTPUT_DIR = "holds_cls_finetuned"


def pad_box(x1, y1, x2, y2, img_w, img_h, padding=0.15):
    """Add padding around a bounding box."""
    box_w = x2 - x1
    box_h = y2 - y1
    pad_x = box_w * padding
    pad_y = box_h * padding
    
    x1_new = max(0, int(x1 - pad_x))
    y1_new = max(0, int(y1 - pad_y))
    x2_new = min(img_w, int(x2 + pad_x))
    y2_new = min(img_h, int(y2 + pad_y))
    
    return x1_new, y1_new, x2_new, y2_new


def generate_crops_from_folder(detector, input_folder, output_base, split_name, conf_threshold, padding):
    """
    Run YOLO on all images in input_folder, generate crops, organize by class.
    """
    input_path = Path(input_folder)
    if not input_path.exists():
        print(f"⚠ Folder not found: {input_folder}")
        return 0
    
    # Find all images
    image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
    image_files = [
        f for f in input_path.rglob('*')
        if f.suffix.lower() in image_extensions
    ]
    
    if not image_files:
        print(f"⚠ No images found in {input_folder}")
        return 0
    
    print(f"\n{'='*60}")
    print(f"Processing {split_name}: {len(image_files)} images")
    print(f"{'='*60}")
    
    # Create output directories
    split_dir = Path(output_base) / split_name
    for class_name in CLASS_NAMES:
        (split_dir / class_name).mkdir(parents=True, exist_ok=True)
    
    # Track crops per class
    crop_counts = {cls: 0 for cls in CLASS_NAMES}
    total_crops = 0
    
    for img_path in tqdm(image_files, desc=f"Generating {split_name} crops"):
        # Read image
        img_bgr = cv2.imread(str(img_path))
        if img_bgr is None:
            continue
        
        img_h, img_w = img_bgr.shape[:2]
        
        # Run YOLO
        results = detector.predict(
            source=img_bgr,
            conf=conf_threshold,
            verbose=False
        )
        
        detections = results[0].boxes
        if len(detections) == 0:
            continue
        
        # Process each detection
        for i, box in enumerate(detections):
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
            conf = box.conf[0].item()
            cls_id = int(box.cls[0].item())
            
            if cls_id >= len(CLASS_NAMES):
                continue
            
            class_name = CLASS_NAMES[cls_id]
            
            # Pad box
            x1_pad, y1_pad, x2_pad, y2_pad = pad_box(x1, y1, x2, y2, img_w, img_h, padding)
            
            # Crop
            crop = img_bgr[y1_pad:y2_pad, x1_pad:x2_pad]
            if crop.size == 0:
                continue
            
            # Save crop
            crop_filename = f"{img_path.stem}_crop{i}_{conf:.2f}.jpg"
            crop_path = split_dir / class_name / crop_filename
            cv2.imwrite(str(crop_path), crop)
            
            crop_counts[class_name] += 1
            total_crops += 1
    
    # Print summary
    print(f"\n✓ {split_name} crops generated: {total_crops}")
    for cls_name, count in crop_counts.items():
        print(f"  {cls_name}: {count}")
    
    return total_crops


def main():
    parser = argparse.ArgumentParser(
        description="Generate classifier crops from raw images using YOLO detector"
    )
    parser.add_argument(
        '--yolo',
        type=str,
        default=YOLO_MODEL,
        help='Path to YOLO model'
    )
    parser.add_argument(
        '--train',
        type=str,
        default='indoor-climbing-gym-hold-classification-dataset/Final_Dataset/train/images',
        help='Path to training images'
    )
    parser.add_argument(
        '--val',
        type=str,
        default='indoor-climbing-gym-hold-classification-dataset/Final_Dataset/valid/images',
        help='Path to validation images'
    )
    parser.add_argument(
        '--test',
        type=str,
        default='indoor-climbing-gym-hold-classification-dataset/Final_Dataset/test/images',
        help='Path to test images'
    )
    parser.add_argument(
        '--output',
        type=str,
        default=OUTPUT_DIR,
        help='Output directory for crops'
    )
    parser.add_argument(
        '--conf',
        type=float,
        default=YOLO_CONF_THRESHOLD,
        help='YOLO confidence threshold'
    )
    parser.add_argument(
        '--padding',
        type=float,
        default=BOX_PADDING,
        help='Box padding fraction (0.15 = 15%%)'
    )
    parser.add_argument(
        '--raw-folder',
        type=str,
        default=None,
        help='Optional: add a folder of raw internet images to training set'
    )
    
    args = parser.parse_args()
    
    print(f"Loading YOLO detector from {args.yolo}...")
    detector = YOLO(args.yolo)
    print("✓ Detector loaded")
    
    # Generate crops for each split
    total = 0
    
    if os.path.exists(args.train):
        total += generate_crops_from_folder(
            detector, args.train, args.output, 'train',
            args.conf, args.padding
        )
    
    if os.path.exists(args.val):
        total += generate_crops_from_folder(
            detector, args.val, args.output, 'val',
            args.conf, args.padding
        )
    
    if os.path.exists(args.test):
        total += generate_crops_from_folder(
            detector, args.test, args.output, 'test',
            args.conf, args.padding
        )
    
    # Optional: add raw images to training set
    if args.raw_folder and os.path.exists(args.raw_folder):
        print("\n" + "="*60)
        print("Adding raw images to training set...")
        print("="*60)
        total += generate_crops_from_folder(
            detector, args.raw_folder, args.output, 'train',
            args.conf, args.padding
        )
    
    print("\n" + "="*60)
    print("COMPLETE")
    print("="*60)
    print(f"Total crops generated: {total}")
    print(f"Output directory: {args.output}")
    print(f"\nNext steps:")
    print(f"1. Review the crops in {args.output}")
    print(f"2. Fine-tune your classifier:")
    print(f"   - Update DATA_DIR in two_phase_train.py to '{args.output}'")
    print(f"   - Reduce PHASE_B_EPOCHS to 5-10 (fine-tuning)")
    print(f"   - Lower learning rate to 5e-5 or 1e-5")
    print(f"   - Run: python two_phase_train.py")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
