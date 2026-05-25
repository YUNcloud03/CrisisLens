import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, f1_score, classification_report, confusion_matrix
)
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use("Agg")  # headless

from utils.config import CLASSES_ZH


def compute_metrics(y_true: list, y_pred: list) -> dict:
    """回傳 accuracy、macro-F1 和 per-class F1。"""
    acc     = accuracy_score(y_true, y_pred)
    macro_f1 = f1_score(y_true, y_pred, average="macro", zero_division=0)
    report   = classification_report(
        y_true, y_pred,
        target_names=CLASSES_ZH,
        output_dict=True,
        zero_division=0,
    )
    return {"accuracy": acc, "macro_f1": macro_f1, "report": report}


def plot_confusion_matrix(y_true: list, y_pred: list, save_path: str) -> str:
    """繪製 confusion matrix 並儲存圖片，回傳路徑。"""
    cm = confusion_matrix(y_true, y_pred, labels=list(range(len(CLASSES_ZH))))
    fig, ax = plt.subplots(figsize=(8, 7))
    fig.patch.set_facecolor("#0d1628")
    ax.set_facecolor("#0d1628")

    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(len(CLASSES_ZH)))
    ax.set_yticks(range(len(CLASSES_ZH)))
    ax.set_xticklabels(CLASSES_ZH, rotation=30, ha="right", color="#e2e8f0", fontsize=9)
    ax.set_yticklabels(CLASSES_ZH, color="#e2e8f0", fontsize=9)
    ax.set_xlabel("預測", color="#94a3b8")
    ax.set_ylabel("實際", color="#94a3b8")
    ax.set_title("Confusion Matrix", color="#38bdf8", fontsize=13)

    for i in range(len(CLASSES_ZH)):
        for j in range(len(CLASSES_ZH)):
            ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                    color="white" if cm[i, j] > cm.max() / 2 else "#e2e8f0", fontsize=10)

    plt.colorbar(im, ax=ax)
    plt.tight_layout()
    plt.savefig(save_path, dpi=120, facecolor=fig.get_facecolor())
    plt.close()
    return save_path


def save_results_csv(records: list[dict], path: str):
    """將預測結果列表存成 CSV。"""
    pd.DataFrame(records).to_csv(path, index=False, encoding="utf-8-sig")
