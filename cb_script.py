import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torchvision import datasets, transforms, models
from pathlib import Path

# ---- config ----
data_root = Path(r"C:\Users\Admin\Desktop\hold_cls")
train_path = data_root / "train"
val_path   = data_root / "valid"

batch_size = 32
num_epochs = 5
lr = 3e-4
device = "cuda" if torch.cuda.is_available() else "cpu"

# ---- transforms ----
train_tfms = transforms.Compose([
    transforms.RandomResizedCrop(224, scale=(0.7, 1.0)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(10),
    transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225]),
])

val_tfms = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225]),
])

# ---- datasets ----
train_path = data_root / "train"
val_path = data_root / "valid"   # your folder is named "valid", not "val"

# Sanity checks
if not train_path.exists():
    raise FileNotFoundError(f"Missing: {train_path}")
if not val_path.exists():
    raise FileNotFoundError(f"Missing: {val_path}")

train_ds = datasets.ImageFolder(str(train_path), transform=train_tfms)
val_ds   = datasets.ImageFolder(str(val_path),   transform=val_tfms)

# On Windows, num_workers=0 avoids common multiprocessing issues
train_loader = DataLoader(train_ds, batch_size=batch_size, shuffle=True, num_workers=0)
val_loader   = DataLoader(val_ds,   batch_size=batch_size, shuffle=False, num_workers=0)

num_classes = len(train_ds.classes)
print("Classes:", train_ds.classes)

# ---- model ----
model = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
model.fc = nn.Linear(model.fc.in_features, num_classes)
model = model.to(device)

criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.AdamW(model.parameters(), lr=lr)

def run_epoch(loader, train: bool):
    model.train(train)
    total_loss, correct, total = 0.0, 0, 0

    for x, y in loader:
        x, y = x.to(device), y.to(device)

        with torch.set_grad_enabled(train):
            logits = model(x)
            loss = criterion(logits, y)

            if train:
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()

        total_loss += loss.item() * x.size(0)
        preds = logits.argmax(dim=1)
        correct += (preds == y).sum().item()
        total += x.size(0)

    return total_loss / total, correct / total

for epoch in range(num_epochs):
    tr_loss, tr_acc = run_epoch(train_loader, train=True)
    va_loss, va_acc = run_epoch(val_loader, train=False)
    print(f"Epoch {epoch+1:02d} | train loss {tr_loss:.4f} acc {tr_acc:.3f} | "
          f"val loss {va_loss:.4f} acc {va_acc:.3f}")

torch.save({"model": model.state_dict(), "classes": train_ds.classes}, "hold_classifier.pt")
print("Saved to hold_classifier.pt")
