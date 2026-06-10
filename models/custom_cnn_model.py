"""自訓 CNN 模型架構定義 ── Phase 1 deployed baseline (v1)。

This is the SINGLE SOURCE OF TRUTH for the production CNN architecture.
The training notebook `train_custom_cnn_kaggle.ipynb` MUST keep its v1
class definition byte-identical to this one — otherwise the saved
`state_dict` will fail to load (mismatched layer names).

v2/v3/v4 ablations live only inside the notebook; they are not deployed.
"""
import torch.nn as nn


class DisasterCNN_v1(nn.Module):
    """4-block CNN baseline for 6-class disaster classification.

    Input  : (B, 3, 224, 224)  RGB image, ImageNet-normalized
    Output : (B, num_classes)   logits (apply softmax for probabilities)
    Params : ~400 K
    """
    def __init__(self, num_classes: int = 6):
        super().__init__()
        self.features = nn.Sequential(
            # Block 1: 224 -> 112
            nn.Conv2d(3, 32, kernel_size=3, padding=1),
            nn.BatchNorm2d(32), nn.ReLU(inplace=True), nn.MaxPool2d(2),
            # Block 2: 112 -> 56
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64), nn.ReLU(inplace=True), nn.MaxPool2d(2),
            # Block 3: 56 -> 28
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.BatchNorm2d(128), nn.ReLU(inplace=True), nn.MaxPool2d(2),
            # Block 4: 28 -> 14
            nn.Conv2d(128, 256, kernel_size=3, padding=1),
            nn.BatchNorm2d(256), nn.ReLU(inplace=True), nn.MaxPool2d(2),
        )
        self.classifier = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),
            nn.Flatten(),
            nn.Dropout(0.3),
            nn.Linear(256, num_classes),
        )

    def forward(self, x):
        return self.classifier(self.features(x))
