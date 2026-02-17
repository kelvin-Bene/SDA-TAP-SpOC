"""
Neural network model definitions for UCTP Lab ML training.

Provides lightweight PyTorch models for:
  - Observation clustering (learned feature embeddings)
  - State propagation (sequence-to-state prediction)

Falls back gracefully if PyTorch is not installed.
"""

from typing import Optional

from loguru import logger

_TORCH_AVAILABLE: Optional[bool] = None


def _check_torch():
    global _TORCH_AVAILABLE
    if _TORCH_AVAILABLE is None:
        try:
            import torch  # noqa: F401

            _TORCH_AVAILABLE = True
        except ImportError:
            _TORCH_AVAILABLE = False
            logger.warning("PyTorch is not installed – ML models unavailable")
    return _TORCH_AVAILABLE


class ClusteringMLP:
    """
    Simple MLP that embeds observations into a latent space
    where same-object observations cluster together.

    Architecture: Input(7) -> FC(64) -> ReLU -> FC(32) -> ReLU -> FC(embed_dim)
    Trained with contrastive or triplet loss.
    """

    def __init__(self, embed_dim: int = 16):
        if not _check_torch():
            raise ImportError("PyTorch is required for ClusteringMLP")

        import torch.nn as nn

        self.embed_dim = embed_dim
        self.model = nn.Sequential(
            nn.Linear(7, 64),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, embed_dim),
        )

    def forward(self, x):
        import torch.nn.functional as F

        out = self.model(x)
        return F.normalize(out, dim=-1)

    def parameters(self):
        return self.model.parameters()

    def train(self):
        self.model.train()

    def eval(self):
        self.model.eval()

    def state_dict(self):
        return self.model.state_dict()

    def load_state_dict(self, state_dict):
        self.model.load_state_dict(state_dict)


class PropagationLSTM:
    """
    LSTM-based model that predicts the next state vector
    from a sequence of previous state vectors.

    Architecture: LSTM(6, hidden=64, layers=2) -> FC(6)
    """

    def __init__(self, hidden_dim: int = 64, num_layers: int = 2):
        if not _check_torch():
            raise ImportError("PyTorch is required for PropagationLSTM")

        import torch.nn as nn

        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.lstm = nn.LSTM(
            input_size=6,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.1,
        )
        self.fc = nn.Linear(hidden_dim, 6)

    def forward(self, x):
        # x: (batch, seq_len, 6)
        lstm_out, _ = self.lstm(x)
        # Use last timestep
        last = lstm_out[:, -1, :]
        return self.fc(last)

    def parameters(self):
        import itertools

        return itertools.chain(self.lstm.parameters(), self.fc.parameters())

    def train(self):
        self.lstm.train()
        self.fc.train()

    def eval(self):
        self.lstm.eval()
        self.fc.eval()

    def state_dict(self):
        return {
            "lstm": self.lstm.state_dict(),
            "fc": self.fc.state_dict(),
        }

    def load_state_dict(self, state_dict):
        self.lstm.load_state_dict(state_dict["lstm"])
        self.fc.load_state_dict(state_dict["fc"])
