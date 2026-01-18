# climBright
A rock climbing hold classifier

## Run Everything (Local)

### 0) Prereqs
- MongoDB server (`mongod`) installed (macOS: `brew install mongodb-community@7.0`)
- Python 3.10+ and Node 18+

### 1) Put model weights in place
- ConvNeXt classifier: place `best_convnext_two_phase.pt` in this folder (same level as `main.py`).
- YOLO detector weights: default path is `runs/detect/train2/weights/best.pt`.

If your files live somewhere else, set env vars when starting FastAPI:
- `CONVNEXT_MODEL_PATH=/absolute/path/to/best_convnext_two_phase.pt`
- `YOLO_MODEL_PATH=/absolute/path/to/best.pt`

### 2) Install Python deps
```bash
cd climBright
pip3 install -r requirements.txt
```

### 3) Start MongoDB (Terminal 1)
```bash
cd climBright
./scripts/start_mongo.sh
```

### 4) Start FastAPI on port 9000 (Terminal 2)
```bash
cd climBright

# optional overrides
export CONVNEXT_MODEL_PATH="./best_convnext_two_phase.pt"
export YOLO_MODEL_PATH="./runs/detect/train2/weights/best.pt"

# allow browser calls from the web server origin
export FRONTEND_ORIGINS="http://127.0.0.1:6769,http://localhost:6769"

./scripts/start_fastapi.sh 9000
```

### 5) Start the web app (Terminal 3)
```bash
cd climBright
./scripts/start_web.sh
```

Open:
- `http://127.0.0.1:6769/login`

### 6) Smoke test
- Register / log in
- Go to `/holds` and upload a JPG/PNG
- Go to `/wall` and upload a wall photo; you should see hold markers + a coach response

Optional API test (replace `sample.jpg`):
```bash
B64=$(base64 -i sample.jpg | tr -d '\n')
curl -s http://127.0.0.1:9000/classifier/upload \
	-H 'Content-Type: application/json' \
	-d "{\"filename\":\"sample.jpg\",\"content_type\":\"image/jpeg\",\"data\":\"$B64\"}" \
	| python3 -m json.tool
```

---
to train a model to classify climbing holds from images

2 option:
1. Use a pre-trained model (ResNet50) and fine-tune it on a dataset of climbing hold images.
- run "two_phases_train.py"

2. train a yolo detector small model from scratch on a dataset of climbing hold images.
``` Bash   
yolo detect train model=yolov8n.pt data=data.yaml imgsz=640 epochs=50 batch=16 device=gpu  # use cpu if no gpu: device=cpu
```

validator script:
``` Bash
python predict.py -m 'path/to/your/model.pt' -i 'path/to/your/images/'
```

data.yaml - describes the types of things to look for in the detector model(yolo)


to detect and classify holds in an image:
``` Bash
python detect_and_classify.py -i 'path/to/your/images/' -y 'path/to/yolo/detector-model' -c 'path/to/your/classifier-model'
```

# Requirements
- see requirements.txt


To turn on a web API server using FastAPI on port 9000:
``` Bash 
uvicorn main:app --reload --port 9000 
```