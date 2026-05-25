"""
ResNet50 Linear Probe 訓練腳本。

自動讀取 data/crisis_images/ 下的資料夾結構：
    Damaged_Infrastructure/  → 地震或建築損壞
    Fire_Disaster/           → 火災
    Land_Disaster/           → 土石流或坍方
    Water_Disaster/          → 淹水
    Non_Damage/              → 其他或無明顯災害

執行方式：
    python models/train_resnet.py
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import torch
import torch.nn as nn
import numpy as np
from PIL import ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True   # 允許讀取截斷/損壞的圖片
from torch.utils.data import DataLoader, WeightedRandomSampler
from torchvision import datasets, transforms, models
from sklearn.metrics import classification_report
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from utils.config import BATCH_SIZE, LEARNING_RATE, EPOCHS, RESNET_WEIGHTS

DATA_DIR = "data/crisis_images"
OUT_DIR  = "outputs"
os.makedirs(OUT_DIR, exist_ok=True)

# ── 資料夾名稱 → 中文類別標籤對照 ────────────────────────────
FOLDER_TO_ZH = {
    "Damaged_Infrastructure": "地震或建築損壞",
    "Fire_Disaster":          "火災",
    "Land_Disaster":          "土石流或坍方",
    "Water_Disaster":         "淹水",
    "Non_Damage":             "其他或無明顯災害",
}

# ── Transforms ───────────────────────────────────────────────
train_tf = transforms.Compose([
    transforms.RandomResizedCrop(224),
    transforms.RandomHorizontalFlip(),
    transforms.RandomVerticalFlip(p=0.1),
    transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3),
    transforms.RandomRotation(15),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])
val_tf = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])


def build_model(num_classes: int) -> nn.Module:
    model = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V2)
    for p in model.parameters():
        p.requires_grad = False          # freeze backbone
    model.fc = nn.Linear(model.fc.in_features, num_classes)
    return model


def make_weighted_sampler(dataset, indices):
    """
    WeightedRandomSampler：讓每個 epoch 每個類別被抽到的機率相等，
    解決 Non_Damage 佔多數導致的類別不平衡問題。
    """
    targets = [dataset.targets[i] for i in indices]
    class_counts = np.bincount(targets)
    class_weights = 1.0 / class_counts.astype(float)
    sample_weights = [class_weights[t] for t in targets]
    return WeightedRandomSampler(sample_weights, num_samples=len(sample_weights), replacement=True)


def train():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")

    # ── Dataset ──────────────────────────────────────────────
    full_ds    = datasets.ImageFolder(DATA_DIR, transform=train_tf)
    num_classes = len(full_ds.classes)
    zh_labels  = [FOLDER_TO_ZH.get(c, c) for c in full_ds.classes]

    print(f"\n類別對照：")
    for folder, zh in zip(full_ds.classes, zh_labels):
        count = full_ds.targets.count(full_ds.class_to_idx[folder])
        print(f"  {folder:35s} → {zh}  ({count} 張)")

    # ── 儲存 class mapping 供推論時使用 ──────────────────────
    mapping = {
        "classes":    full_ds.classes,
        "zh_labels":  zh_labels,
        "class_to_idx": full_ds.class_to_idx,
    }
    mapping_path = RESNET_WEIGHTS.replace(".pth", "_classes.json")
    with open(mapping_path, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)
    print(f"\nClass mapping 已儲存 → {mapping_path}")

    # ── Train / Val 分割 ─────────────────────────────────────
    n_total = len(full_ds)
    n_val   = int(n_total * 0.2)
    n_train = n_total - n_val
    train_ds, val_ds = torch.utils.data.random_split(
        full_ds, [n_train, n_val],
        generator=torch.Generator().manual_seed(42)
    )
    # val 用 val_tf（不做 augmentation）
    val_ds.dataset.transform = val_tf

    # WeightedRandomSampler 解決類別不平衡
    sampler = make_weighted_sampler(full_ds, train_ds.indices)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE,
                              sampler=sampler, num_workers=0)
    val_loader   = DataLoader(val_ds, batch_size=BATCH_SIZE,
                              shuffle=False, num_workers=0)

    print(f"\nTrain: {n_train}  Val: {n_val}  Classes: {num_classes}")

    # ── Model ────────────────────────────────────────────────
    model     = build_model(num_classes).to(device)
    optimizer = torch.optim.Adam(model.fc.parameters(), lr=LEARNING_RATE)
    loss_fn   = nn.CrossEntropyLoss()
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=2, gamma=0.5)

    history = {"train_loss": [], "val_acc": []}

    for epoch in range(1, EPOCHS + 1):
        # ── Train ────────────────────────────────────────
        model.train()
        total_loss = 0.0
        for imgs, labels in train_loader:
            imgs, labels = imgs.to(device), labels.to(device)
            optimizer.zero_grad()
            loss = loss_fn(model(imgs), labels)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        scheduler.step()

        # ── Validate ─────────────────────────────────────
        model.eval()
        correct = total = 0
        all_pred, all_true = [], []
        with torch.no_grad():
            for imgs, labels in val_loader:
                imgs, labels = imgs.to(device), labels.to(device)
                preds = model(imgs).argmax(1)
                correct += (preds == labels).sum().item()
                total   += labels.size(0)
                all_pred.extend(preds.cpu().tolist())
                all_true.extend(labels.cpu().tolist())

        val_acc  = correct / total
        avg_loss = total_loss / len(train_loader)
        history["train_loss"].append(avg_loss)
        history["val_acc"].append(val_acc)
        print(f"Epoch {epoch}/{EPOCHS}  Loss: {avg_loss:.4f}  Val Acc: {val_acc:.4f}")

    # ── Final report ─────────────────────────────────────────
    print("\n" + classification_report(
        all_true, all_pred,
        target_names=zh_labels,
        zero_division=0
    ))

    # ── Save model ───────────────────────────────────────────
    torch.save(model.state_dict(), RESNET_WEIGHTS)
    print(f"Model saved → {RESNET_WEIGHTS}")

    # ── Training curve ───────────────────────────────────────
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    fig.patch.set_facecolor("#0d1628")
    for ax in (ax1, ax2):
        ax.set_facecolor("#0d1628")

    ax1.plot(history["train_loss"], color="#38bdf8", linewidth=2)
    ax1.set_title("Training Loss", color="#e2e8f0")
    ax1.set_xlabel("Epoch", color="#94a3b8")
    ax1.tick_params(colors="#94a3b8")

    ax2.plot(history["val_acc"], color="#4ade80", linewidth=2)
    ax2.set_title("Val Accuracy", color="#e2e8f0")
    ax2.set_xlabel("Epoch", color="#94a3b8")
    ax2.set_ylim(0, 1)
    ax2.tick_params(colors="#94a3b8")

    plt.tight_layout()
    curve_path = f"{OUT_DIR}/resnet_training_curve.png"
    plt.savefig(curve_path, dpi=120, facecolor=fig.get_facecolor())
    plt.close()
    print(f"Training curve → {curve_path}")


if __name__ == "__main__":
    train()
