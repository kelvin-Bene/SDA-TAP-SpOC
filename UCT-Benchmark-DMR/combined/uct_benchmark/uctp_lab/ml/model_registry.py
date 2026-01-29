"""
Model registry for UCTP Lab ML module.

Handles saving, loading, and versioning of trained models
on the local filesystem.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


DEFAULT_REGISTRY_DIR = Path(__file__).parent.parent.parent.parent / "data" / "ml_models"


class ModelRegistry:
    """
    Manages trained model artefacts on disk.

    Directory layout:
        registry_dir/
            <model_name>/
                v1/
                    model.pt
                    metadata.json
                v2/
                    ...
    """

    def __init__(self, registry_dir: Optional[Path] = None):
        self.registry_dir = registry_dir or DEFAULT_REGISTRY_DIR
        self.registry_dir.mkdir(parents=True, exist_ok=True)

    def save_model(
        self,
        name: str,
        model_state: Any,
        metadata: Dict[str, Any],
    ) -> str:
        """
        Save a model with auto-incrementing version.

        Returns the version string (e.g. "v3").
        """
        model_dir = self.registry_dir / name
        model_dir.mkdir(parents=True, exist_ok=True)

        # Find next version
        existing = sorted(model_dir.iterdir()) if model_dir.exists() else []
        versions = [
            int(d.name[1:]) for d in existing if d.is_dir() and d.name.startswith("v")
        ]
        next_v = max(versions, default=0) + 1
        version = f"v{next_v}"
        version_dir = model_dir / version
        version_dir.mkdir()

        # Save model weights
        model_path = version_dir / "model.pt"
        try:
            import torch

            torch.save(model_state, str(model_path))
        except ImportError:
            # Fallback: save as numpy
            import numpy as np

            np.savez(str(version_dir / "model.npz"), **{
                k: v.cpu().numpy() if hasattr(v, "cpu") else v
                for k, v in (model_state.items() if isinstance(model_state, dict) else {})
            })
            model_path = version_dir / "model.npz"

        # Save metadata
        meta = {
            "name": name,
            "version": version,
            "created_at": datetime.utcnow().isoformat(),
            "model_path": str(model_path),
            **metadata,
        }
        with open(version_dir / "metadata.json", "w") as f:
            json.dump(meta, f, indent=2, default=str)

        logger.info(f"Saved model {name} {version} to {version_dir}")
        return version

    def load_model(self, name: str, version: Optional[str] = None) -> Dict[str, Any]:
        """
        Load a model's state dict and metadata.

        If version is None, loads the latest version.
        """
        model_dir = self.registry_dir / name
        if not model_dir.exists():
            raise FileNotFoundError(f"Model {name} not found in registry")

        if version is None:
            versions = sorted([
                d for d in model_dir.iterdir()
                if d.is_dir() and d.name.startswith("v")
            ])
            if not versions:
                raise FileNotFoundError(f"No versions found for model {name}")
            version_dir = versions[-1]
        else:
            version_dir = model_dir / version
            if not version_dir.exists():
                raise FileNotFoundError(f"Version {version} not found for model {name}")

        # Load metadata
        meta_path = version_dir / "metadata.json"
        metadata = {}
        if meta_path.exists():
            with open(meta_path) as f:
                metadata = json.load(f)

        # Load model weights
        model_state = None
        pt_path = version_dir / "model.pt"
        npz_path = version_dir / "model.npz"

        if pt_path.exists():
            try:
                import torch

                model_state = torch.load(str(pt_path), map_location="cpu", weights_only=True)
            except ImportError:
                logger.warning("PyTorch not available, cannot load .pt model")
        elif npz_path.exists():
            import numpy as np

            model_state = dict(np.load(str(npz_path)))

        return {
            "state_dict": model_state,
            "metadata": metadata,
        }

    def list_models(self) -> List[Dict[str, Any]]:
        """List all models and their latest versions."""
        models = []
        if not self.registry_dir.exists():
            return models

        for model_dir in sorted(self.registry_dir.iterdir()):
            if not model_dir.is_dir():
                continue

            versions = sorted([
                d for d in model_dir.iterdir()
                if d.is_dir() and d.name.startswith("v")
            ])
            if not versions:
                continue

            latest = versions[-1]
            meta_path = latest / "metadata.json"
            metadata = {}
            if meta_path.exists():
                with open(meta_path) as f:
                    metadata = json.load(f)

            models.append({
                "name": model_dir.name,
                "latest_version": latest.name,
                "total_versions": len(versions),
                "metadata": metadata,
            })

        return models

    def delete_model(self, name: str, version: Optional[str] = None) -> bool:
        """Delete a model or specific version."""
        import shutil

        model_dir = self.registry_dir / name
        if not model_dir.exists():
            return False

        if version:
            version_dir = model_dir / version
            if version_dir.exists():
                shutil.rmtree(version_dir)
                return True
            return False
        else:
            shutil.rmtree(model_dir)
            return True
