"""
Training loop for UCTP Lab ML models.

Provides a generic training harness that works with both the
ClusteringMLP and PropagationLSTM models.
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import numpy as np
from loguru import logger


@dataclass
class TrainingConfig:
    """Configuration for an ML training run."""

    epochs: int = 50
    batch_size: int = 32
    learning_rate: float = 1e-3
    weight_decay: float = 1e-5
    early_stopping_patience: int = 10
    validation_split: float = 0.2
    seed: int = 42


@dataclass
class TrainingResult:
    """Result from a training run."""

    train_losses: List[float] = field(default_factory=list)
    val_losses: List[float] = field(default_factory=list)
    best_epoch: int = 0
    best_val_loss: float = float("inf")
    final_metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "train_losses": self.train_losses,
            "val_losses": self.val_losses,
            "best_epoch": self.best_epoch,
            "best_val_loss": self.best_val_loss,
            "final_metrics": self.final_metrics,
        }


ProgressCallback = Callable[[int, float, float], None]


def train_model(
    model,
    features: np.ndarray,
    targets: np.ndarray,
    config: TrainingConfig,
    progress_callback: Optional[ProgressCallback] = None,
) -> TrainingResult:
    """
    Train a model on the provided data.

    Args:
        model: A model with forward(), parameters(), train(), eval() methods.
        features: Input feature array.
        targets: Target array.
        config: Training configuration.
        progress_callback: Optional (epoch, train_loss, val_loss) callback.

    Returns:
        TrainingResult with loss history and metrics.
    """
    try:
        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader, TensorDataset
    except ImportError:
        logger.error("PyTorch is required for training")
        result = TrainingResult()
        result.final_metrics = {"error": "PyTorch not installed"}
        return result

    torch.manual_seed(config.seed)

    # Convert to tensors
    X = torch.tensor(features, dtype=torch.float32)
    if targets.dtype in (np.int32, np.int64):
        y = torch.tensor(targets, dtype=torch.long)
        criterion = nn.CrossEntropyLoss()
    else:
        y = torch.tensor(targets, dtype=torch.float32)
        criterion = nn.MSELoss()

    # Train/val split
    n = len(X)
    n_val = int(n * config.validation_split)
    n_train = n - n_val

    indices = torch.randperm(n)
    train_idx = indices[:n_train]
    val_idx = indices[n_train:]

    train_ds = TensorDataset(X[train_idx], y[train_idx])
    val_ds = TensorDataset(X[val_idx], y[val_idx])

    train_loader = DataLoader(train_ds, batch_size=config.batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=config.batch_size)

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=config.learning_rate,
        weight_decay=config.weight_decay,
    )

    result = TrainingResult()
    best_state = None
    patience_counter = 0

    for epoch in range(config.epochs):
        # Train
        model.train()
        train_loss = 0.0
        n_batches = 0
        for batch_x, batch_y in train_loader:
            optimizer.zero_grad()
            out = model.forward(batch_x)
            loss = criterion(out, batch_y)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()
            n_batches += 1

        avg_train_loss = train_loss / max(n_batches, 1)
        result.train_losses.append(avg_train_loss)

        # Validate
        model.eval()
        val_loss = 0.0
        n_val_batches = 0
        with torch.no_grad():
            for batch_x, batch_y in val_loader:
                out = model.forward(batch_x)
                loss = criterion(out, batch_y)
                val_loss += loss.item()
                n_val_batches += 1

        avg_val_loss = val_loss / max(n_val_batches, 1)
        result.val_losses.append(avg_val_loss)

        if progress_callback:
            progress_callback(epoch, avg_train_loss, avg_val_loss)

        # Early stopping
        if avg_val_loss < result.best_val_loss:
            result.best_val_loss = avg_val_loss
            result.best_epoch = epoch
            best_state = {k: v.clone() for k, v in model.state_dict().items()}
            patience_counter = 0
        else:
            patience_counter += 1
            if patience_counter >= config.early_stopping_patience:
                logger.info(f"Early stopping at epoch {epoch}")
                break

    # Restore best weights
    if best_state is not None:
        model.load_state_dict(best_state)

    result.final_metrics = {
        "final_train_loss": result.train_losses[-1] if result.train_losses else 0,
        "final_val_loss": result.val_losses[-1] if result.val_losses else 0,
        "best_val_loss": result.best_val_loss,
        "best_epoch": result.best_epoch,
        "total_epochs": len(result.train_losses),
    }

    return result
