"""
本機訓練 CLIP Linear Probe（用 Colab 抽好的特徵快取，CPU 幾秒完成）。

一次性準備：
    把 Colab/Drive 的 feat_train.npz / feat_dev.npz / feat_test.npz
    （約 200MB）下載放到 CrisisLens/features/

執行：
    python models/train_linear_probe.py                  # 預設 sqrt 權重
    python models/train_linear_probe.py --weighting inverse
    python models/train_linear_probe.py --weighting none --epochs 500

訓練好的 clip_linear_head.pth 會直接覆蓋到 models/，重啟 streamlit 即生效。
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import argparse
import numpy as np
import torch
import torch.nn as nn
from sklearn.metrics import classification_report, confusion_matrix

from utils.config import CLASSES_EN

FEATURES_DIR = os.path.join(os.path.dirname(__file__), "..", "features")
OUT_PATH     = os.path.join(os.path.dirname(__file__), "clip_linear_head.pth")
CLIP_MODEL   = "ViT-L/14"


def _load(split):
    path = os.path.join(FEATURES_DIR, f"feat_{split}.npz")
    if not os.path.exists(path):
        sys.exit(f"[錯誤] 找不到 {path}\n   請先把 Colab/Drive 的 feat_{split}.npz 放到 features/")
    d = np.load(path)
    return d["X"].astype("float32"), d["y"].astype("int64")


def _class_weights(y, mode, k):
    counts = np.bincount(y, minlength=k)
    inv = counts.sum() / (k * np.maximum(counts, 1))
    if   mode == "inverse": w = inv
    elif mode == "sqrt":    w = np.sqrt(inv)
    elif mode == "none":    w = np.ones(k)
    else: sys.exit(f"未知 weighting: {mode}")
    return torch.tensor(w, dtype=torch.float32), counts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weighting", default="sqrt", choices=["sqrt", "inverse", "none"],
                    help="class weight 模式（sqrt=較平衡，inverse=最偏向稀有類，none=不加權）")
    ap.add_argument("--epochs", type=int, default=300)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--weight-decay", type=float, default=1e-4,
                    help="L2 正則；過大會壓扁信心，過小可能過擬合")
    args = ap.parse_args()

    Xtr, ytr = _load("train")
    Xdv, ydv = _load("dev")
    Xte, yte = _load("test")
    k       = len(CLASSES_EN)
    in_dim  = Xtr.shape[1]
    print(f"特徵維度 {in_dim} | train {len(ytr)}  dev {len(ydv)}  test {len(yte)}")

    Xtr_t, ytr_t = torch.tensor(Xtr), torch.tensor(ytr)
    Xdv_t, ydv_t = torch.tensor(Xdv), torch.tensor(ydv)

    class_w, counts = _class_weights(ytr, args.weighting, k)
    print(f"weighting={args.weighting}  class weights: {np.round(class_w.numpy(), 3)}")
    print("各類別 train 張數:", dict(zip(range(k), counts.tolist())))

    clf   = nn.Linear(in_dim, k)
    opt   = torch.optim.AdamW(clf.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    lossf = nn.CrossEntropyLoss(weight=class_w)

    best_acc, best_state = 0.0, None
    for epoch in range(1, args.epochs + 1):
        clf.train(); opt.zero_grad()
        loss = lossf(clf(Xtr_t), ytr_t); loss.backward(); opt.step()
        if epoch % 10 == 0:
            clf.eval()
            with torch.no_grad():
                acc = (clf(Xdv_t).argmax(1) == ydv_t).float().mean().item()
            if acc > best_acc:
                best_acc = acc
                best_state = {kk: v.clone() for kk, v in clf.state_dict().items()}
    clf.load_state_dict(best_state)
    print(f"\n最佳 dev acc: {best_acc:.4f}")

    # ── 溫度校準（在 dev 集上學一個溫度，修正信心，不影響準確率/排序）──
    clf.eval()
    with torch.no_grad():
        logits_dev = clf(Xdv_t)
    temperature = nn.Parameter(torch.ones(1))
    opt_t = torch.optim.LBFGS([temperature], lr=0.01, max_iter=80)
    def _closure():
        opt_t.zero_grad()
        loss = nn.functional.cross_entropy(logits_dev / temperature.clamp(min=1e-2), ydv_t)
        loss.backward(); return loss
    opt_t.step(_closure)
    T = float(temperature.detach().clamp(min=1e-2).item())
    print(f"校準溫度 T = {T:.3f}  （<1 代表原本信心不足、會被調尖）")

    # ── test 評估 ──
    clf.eval()
    with torch.no_grad():
        pred = clf(torch.tensor(Xte)).argmax(1).numpy()
    print("\n" + classification_report(yte, pred, target_names=CLASSES_EN, zero_division=0))
    print("Confusion matrix (row=真實, col=預測):")
    cm = confusion_matrix(yte, pred, labels=list(range(k)))
    print("      " + " ".join(f"{i:>5d}" for i in range(k)))
    for i, row in enumerate(cm):
        print(f"[{i}] " + " ".join(f"{v:>5d}" for v in row), CLASSES_EN[i])

    # ── 匯出 ──
    torch.save({
        "state_dict":  clf.state_dict(),
        "classes_en":  CLASSES_EN,
        "clip_model":  CLIP_MODEL,
        "in_dim":      in_dim,
        "temperature": T,
    }, OUT_PATH)
    print(f"\n[完成] 已存 {OUT_PATH}（重啟 streamlit 生效）")


if __name__ == "__main__":
    main()
