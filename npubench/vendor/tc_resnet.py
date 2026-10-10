"""
TC-ResNet: Temporal Convolutional ResNet for keyword spotting.
Based on: "Temporal Convolution for Real-time Keyword Spotting on Mobile Devices" (Choi et al., 2019).
~80K parameters, 94%+ on 10-class Google Speech Commands.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class DepthwiseConv1D(nn.Module):
    """Depthwise separable 1D convolution."""

    def __init__(self, in_ch, out_ch, kernel_size, stride=1, padding=0):
        super().__init__()
        self.depthwise = nn.Conv1d(in_ch, in_ch, kernel_size, stride=stride,
                                   padding=padding, groups=in_ch)
        self.pointwise = nn.Conv1d(in_ch, out_ch, 1)

    def forward(self, x):
        return self.pointwise(self.depthwise(x))


class TCBottleneck(nn.Module):
    """TC-ResNet bottleneck block with depthwise convolutions."""

    def __init__(self, in_ch, out_ch, kernel_size=9, stride=1):
        super().__init__()
        self.conv1 = nn.Conv1d(in_ch, out_ch, 1)
        self.bn1 = nn.BatchNorm1d(out_ch)
        self.dw_conv = DepthwiseConv1D(out_ch, out_ch, kernel_size,
                                        stride=stride, padding=kernel_size // 2)
        self.bn2 = nn.BatchNorm1d(out_ch)
        self.conv2 = nn.Conv1d(out_ch, out_ch, 1)
        self.bn3 = nn.BatchNorm1d(out_ch)

        self.shortcut = nn.Sequential()
        if stride != 1 or in_ch != out_ch:
            self.shortcut = nn.Sequential(
                nn.Conv1d(in_ch, out_ch, 1, stride=stride),
                nn.BatchNorm1d(out_ch),
            )

    def forward(self, x):
        residual = self.shortcut(x)
        out = F.relu(self.bn1(self.conv1(x)))
        out = F.relu(self.bn2(self.dw_conv(out)))
        out = self.bn3(self.conv2(out))
        out = F.relu(out + residual)
        return out


class TCResNet(nn.Module):
    """
    TC-ResNet for keyword spotting.
    Input: (batch, 1, n_mels, T) mel-spectrogram
    Output: (batch, num_classes)
    """

    def __init__(self, config: dict):
        super().__init__()
        num_classes = config.get("num_classes", 10)
        mel_bins = config.get("mel_bins", 40)
        base_filters = config.get("base_filters", 48)
        dropout = config.get("dropout", 0.3)

        # Initial conv: (1, n_mels, T) -> (base_filters, T)
        self.conv0 = nn.Conv1d(mel_bins, base_filters, kernel_size=3, stride=1, padding=1)
        self.bn0 = nn.BatchNorm1d(base_filters)

        # Bottlenecks
        channels = [base_filters, base_filters * 2, base_filters * 4, base_filters * 4]
        strides = [1, 2, 2, 2]
        kernels = [9, 9, 9, 9]
        self.blocks = nn.ModuleList()
        in_ch = base_filters
        for i in range(len(channels)):
            self.blocks.append(
                TCBottleneck(in_ch, channels[i], kernel_size=kernels[i], stride=strides[i])
            )
            in_ch = channels[i]

        self.gap = nn.AdaptiveAvgPool1d(1)
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(in_ch, num_classes)

    def forward(self, x):
        """x: (B, C=1, n_mels, T) mel-spec"""
        # Squeeze channel dim: (B, n_mels, T)
        x = x.squeeze(1)
        x = F.relu(self.bn0(self.conv0(x)))
        for block in self.blocks:
            x = block(x)
        x = self.gap(x).squeeze(-1)
        x = self.dropout(x)
        x = self.fc(x)
        return x