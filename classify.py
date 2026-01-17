from pathlib import Path
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image

CKPT_PATH = Path("hold_multilabel.pt")   # your checkpoint
IMAGE_PATH = Path("test.jpg")            # image to classify

device = "cuda" if torch.cuda.is_available() else "cpu"

# must match validation preprocessing (no random aug)
tfm = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225]),
])

# load checkpoint
ckpt = torch.load(CKPT_PATH, map_location="cpu")
state = ckpt["model"]
label_names = ckpt.get("label_names") or [f"label_{i}" for i in range(state["fc.weight"].shape[0])]

num_out = state["fc.weight"].shape[0]

# rebuild model
model = models.resnet18(weights=None)
model.fc = nn.Linear(model.fc.in_features, num_out)
model.load_state_dict(state)
model = model.to(device)
model.eval()

# load image
img = Image.open(IMAGE_PATH).convert("RGB")
x = tfm(img).unsqueeze(0).to(device)

with torch.no_grad():
    logits = model(x)[0].cpu()
    probs = torch.sigmoid(logits)  # multi-label probabilities

print("Image:", IMAGE_PATH)
for name, p in zip(label_names, probs.tolist()):
    print(f"{name}: {p:.4f}")

# if you want a yes/no decision:
threshold = 0.5
active = [name for name, p in zip(label_names, probs.tolist()) if p >= threshold]
print(f"\nLabels with prob >= {threshold}: {active if active else 'none'}")
