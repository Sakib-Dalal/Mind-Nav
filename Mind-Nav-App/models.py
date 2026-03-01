"""
Mind-Nav — Model Definitions & Manager
═══════════════════════════════════════
All PyTorch model architectures and the unified ModelManager that
loads sklearn + PyTorch models and runs inference.
"""

import os
import numpy as np

from config import MODEL_DIR, WIN_LEN, N_FEATURES
from features import extract_features


# ══════════════════════════════════════════════════════════════════════════════
#  PyTorch Model Classes (must match training notebook)
# ══════════════════════════════════════════════════════════════════════════════
def build_torch_classes():
    """Import torch and define all model classes. Returns them as a bundle."""
    import os
    os.environ.setdefault("PYTORCH_MPS_DISABLE_VALIDATION", "1")
    os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
    import torch
    import torch.nn as nn

    class BCIConvBlock(nn.Module):
        def __init__(self, in_ch, out_ch, kernel=7, pool=2, dropout=0.3):
            super().__init__()
            self.block = nn.Sequential(
                nn.Conv1d(in_ch, out_ch, kernel_size=kernel, padding=kernel // 2),
                nn.BatchNorm1d(out_ch),
                nn.ReLU(),
                nn.MaxPool1d(pool),
                nn.Dropout(dropout),
            )

        def forward(self, x):
            return self.block(x)

    class BCIFNN(nn.Module):
        def __init__(self, in_features=42, hidden=None, dropout=0.4, n_classes=2):
            super().__init__()
            if hidden is None:
                hidden = [128, 64, 32]
            layers, prev = [], in_features
            for h in hidden:
                layers += [nn.Linear(prev, h), nn.BatchNorm1d(h),
                           nn.ReLU(), nn.Dropout(dropout)]
                prev = h
            layers.append(nn.Linear(prev, n_classes))
            self.net = nn.Sequential(*layers)

        def forward(self, x):
            return self.net(x)

    class BCICNN(nn.Module):
        def __init__(self, win_len=256, n_classes=2, dropout=0.4):
            super().__init__()
            self.encoder = nn.Sequential(
                BCIConvBlock(1, 32, kernel=15, pool=2, dropout=dropout),
                BCIConvBlock(32, 64, kernel=9, pool=2, dropout=dropout),
                BCIConvBlock(64, 128, kernel=5, pool=2, dropout=dropout),
            )
            self.gap = nn.AdaptiveAvgPool1d(1)
            self.classifier = nn.Sequential(
                nn.Flatten(),
                nn.Linear(128, 64), nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(64, n_classes),
            )

        def forward(self, x):
            x = x.unsqueeze(1)
            x = self.encoder(x)
            x = self.gap(x)
            return self.classifier(x)

    class BCIHybrid(nn.Module):
        def __init__(self, win_len=256, n_feat=42, dropout=0.4, n_classes=2):
            super().__init__()
            self.cnn_branch = nn.Sequential(
                BCIConvBlock(1, 32, kernel=15, pool=2, dropout=dropout),
                BCIConvBlock(32, 64, kernel=9, pool=2, dropout=dropout),
                BCIConvBlock(64, 128, kernel=5, pool=2, dropout=dropout),
                nn.AdaptiveAvgPool1d(1),
            )
            self.fnn_branch = nn.Sequential(
                nn.Linear(n_feat, 128), nn.BatchNorm1d(128), nn.ReLU(), nn.Dropout(dropout),
                nn.Linear(128, 64), nn.BatchNorm1d(64), nn.ReLU(), nn.Dropout(dropout),
            )
            self.fusion = nn.Sequential(
                nn.Linear(192, 64), nn.BatchNorm1d(64), nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(64, n_classes),
            )

        def forward(self, raw, feat):
            cnn_out = self.cnn_branch(raw.unsqueeze(1)).squeeze(-1)
            fnn_out = self.fnn_branch(feat)
            return self.fusion(torch.cat([cnn_out, fnn_out], dim=1))

    # ── Transformer building blocks ──────────────────────────────────────

    class PatchEmbedding(nn.Module):
        """Split a 1-D EEG window into non-overlapping patches and
        project each patch to *d_model* dimensions."""
        def __init__(self, win_len: int = 256, patch_size: int = 16,
                     d_model: int = 64):
            super().__init__()
            assert win_len % patch_size == 0
            self.patch_size = patch_size
            self.n_patches  = win_len // patch_size
            self.proj       = nn.Linear(patch_size, d_model)

        def forward(self, x):
            B = x.size(0)
            x = x.view(B, self.n_patches, self.patch_size)
            return self.proj(x)

    class PositionalEncoding(nn.Module):
        """Learnable 1-D positional embeddings."""
        def __init__(self, n_positions: int, d_model: int,
                     dropout: float = 0.1):
            super().__init__()
            self.dropout = nn.Dropout(dropout)
            self.pe      = nn.Embedding(n_positions, d_model)

        def forward(self, x):
            positions = torch.arange(x.size(1), device=x.device)
            return self.dropout(x + self.pe(positions))

    class BCITransformer(nn.Module):
        """Patch-based Transformer Encoder for raw EEG classification."""
        def __init__(self, win_len: int = 256, patch_size: int = 16,
                     d_model: int = 64, n_heads: int = 4,
                     n_layers: int = 3, ffn_dim: int = 128,
                     dropout: float = 0.2, n_classes: int = 2):
            super().__init__()
            self.patch_embed = PatchEmbedding(win_len, patch_size, d_model)
            n_patches = win_len // patch_size
            self.cls_token = nn.Parameter(torch.zeros(1, 1, d_model))
            nn.init.trunc_normal_(self.cls_token, std=0.02)
            self.pos_embed = PositionalEncoding(
                n_patches + 1, d_model, dropout)
            encoder_layer = nn.TransformerEncoderLayer(
                d_model=d_model, nhead=n_heads,
                dim_feedforward=ffn_dim, dropout=dropout,
                activation="gelu", batch_first=True, norm_first=True)
            self.transformer = nn.TransformerEncoder(
                encoder_layer, num_layers=n_layers,
                enable_nested_tensor=False)
            self.norm = nn.LayerNorm(d_model)
            self.classifier = nn.Sequential(
                nn.Linear(d_model, d_model // 2), nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(d_model // 2, n_classes))

        def forward(self, x):
            B = x.size(0)
            tokens = self.patch_embed(x)
            cls = self.cls_token.expand(B, -1, -1)
            tokens = torch.cat([cls, tokens], dim=1)
            tokens = self.pos_embed(tokens)
            tokens = self.transformer(tokens)
            tokens = self.norm(tokens)
            return self.classifier(tokens[:, 0, :])

    class BCITransformerHybrid(nn.Module):
        """Transformer (raw EEG) + FNN (features), fused."""
        def __init__(self, win_len: int = 256, patch_size: int = 16,
                     d_model: int = 64, n_heads: int = 4,
                     n_layers: int = 3, ffn_dim: int = 128,
                     n_feat: int = 42, feat_hidden: int = 64,
                     dropout: float = 0.2, n_classes: int = 2):
            super().__init__()
            self.patch_embed = PatchEmbedding(win_len, patch_size, d_model)
            n_patches = win_len // patch_size
            self.cls_token = nn.Parameter(torch.zeros(1, 1, d_model))
            nn.init.trunc_normal_(self.cls_token, std=0.02)
            self.pos_embed = PositionalEncoding(
                n_patches + 1, d_model, dropout)
            encoder_layer = nn.TransformerEncoderLayer(
                d_model=d_model, nhead=n_heads,
                dim_feedforward=ffn_dim, dropout=dropout,
                activation="gelu", batch_first=True, norm_first=True)
            self.transformer = nn.TransformerEncoder(
                encoder_layer, num_layers=n_layers,
                enable_nested_tensor=False)
            self.norm = nn.LayerNorm(d_model)
            self.feat_branch = nn.Sequential(
                nn.Linear(n_feat, 128), nn.BatchNorm1d(128),
                nn.GELU(), nn.Dropout(dropout),
                nn.Linear(128, feat_hidden), nn.BatchNorm1d(feat_hidden),
                nn.GELU(), nn.Dropout(dropout))
            fused_dim = d_model + feat_hidden
            self.fusion = nn.Sequential(
                nn.Linear(fused_dim, fused_dim // 2),
                nn.LayerNorm(fused_dim // 2), nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(fused_dim // 2, n_classes))

        def _transformer_embed(self, x):
            B = x.size(0)
            tokens = self.patch_embed(x)
            cls = self.cls_token.expand(B, -1, -1)
            tokens = torch.cat([cls, tokens], dim=1)
            tokens = self.pos_embed(tokens)
            tokens = self.transformer(tokens)
            return self.norm(tokens)[:, 0, :]

        def forward(self, raw, feat):
            tr_out = self._transformer_embed(raw)
            feat_out = self.feat_branch(feat)
            return self.fusion(torch.cat([tr_out, feat_out], dim=1))

    return (torch, BCIFNN, BCICNN, BCIHybrid,
            BCITransformer, BCITransformerHybrid)


# ══════════════════════════════════════════════════════════════════════════════
#  ModelManager — loads and runs inference for all model types
# ══════════════════════════════════════════════════════════════════════════════
class ModelManager:
    def __init__(self):
        self.ensemble = None
        self.scaler = None
        self.fnn = None
        self.cnn = None
        self.hybrid = None
        self.transformer = None
        self.transformer_hybrid = None
        self.device = None
        self.errors: list[str] = []

    def load_all(self):
        """Load every model file that exists. Errors stored, never raised."""
        model_dir = MODEL_DIR

        # ── sklearn ensemble ──────────────────────────────────────────────
        try:
            import joblib
            from sklearn.utils.validation import check_is_fitted
            path = os.path.join(model_dir, "BCI_MODEL.joblib")
            loaded = joblib.load(path)
            try:
                check_is_fitted(loaded)
                self.ensemble = loaded
            except Exception:
                self.errors.append("BCI_MODEL.joblib: NOT fitted")
        except FileNotFoundError:
            self.errors.append("BCI_MODEL.joblib: file not found")
        except Exception as e:
            self.errors.append(f"BCI_MODEL.joblib: {e}")

        # ── scaler ────────────────────────────────────────────────────────
        try:
            import joblib
            self.scaler = joblib.load(os.path.join(model_dir, "BCI_SCALER.joblib"))
        except FileNotFoundError:
            self.errors.append("BCI_SCALER.joblib: file not found")
        except Exception as e:
            self.errors.append(f"BCI_SCALER.joblib: {e}")

        # ── PyTorch models ────────────────────────────────────────────────
        try:
            (torch, BCIFNN, BCICNN, BCIHybrid,
             BCITransformer, BCITransformerHybrid) = build_torch_classes()
            # CPU inference — avoids MPS CHECK_PFPROJ warnings on Apple Silicon
            self.device = torch.device("cpu")

            specs = [
                ("fnn", "BCI_FNN.pt",
                 lambda: BCIFNN(in_features=N_FEATURES)),
                ("cnn", "BCI_CNN.pt",
                 lambda: BCICNN(win_len=WIN_LEN)),
                ("hybrid", "BCI_Hybrid.pt",
                 lambda: BCIHybrid(win_len=WIN_LEN, n_feat=N_FEATURES)),
                ("transformer", "BCI_Transformer.pt",
                 lambda: BCITransformer(win_len=WIN_LEN)),
                ("transformer_hybrid", "BCI_TransformerHybrid.pt",
                 lambda: BCITransformerHybrid(
                     win_len=WIN_LEN, n_feat=N_FEATURES)),
            ]
            for attr, fname, builder in specs:
                try:
                    model = builder().to(self.device)
                    state = torch.load(os.path.join(model_dir, fname),
                                       map_location=self.device,
                                       weights_only=True)
                    model.load_state_dict(state)
                    model.eval()
                    setattr(self, attr, (model, torch))
                except FileNotFoundError:
                    self.errors.append(f"{fname}: file not found")
                except Exception as e:
                    self.errors.append(f"{fname}: {e}")

        except ImportError:
            self.errors.append("PyTorch not installed — deep-learning models unavailable")

    def available_models(self) -> list[str]:
        out = []
        if self.ensemble and self.scaler:
            out.append("ET+RF Ensemble")
        if self.fnn:
            out.append("FNN")
        if self.cnn:
            out.append("CNN")
        if self.hybrid:
            out.append("Hybrid CNN+FNN")
        if self.transformer:
            out.append("Transformer")
        if self.transformer_hybrid:
            out.append("Transformer+FNN")
        return out

    # ── Private helpers ───────────────────────────────────────────────────

    def _prep_features(self, raw: np.ndarray) -> np.ndarray:
        feats = extract_features(raw).reshape(1, -1)
        if self.scaler is not None:
            feats = self.scaler.transform(feats)
        return feats.astype(np.float32)

    @staticmethod
    def _prep_raw(raw: np.ndarray) -> np.ndarray:
        w = raw.astype(np.float32)
        w = (w - w.mean()) / (w.std() + 1e-8)
        if len(w) < WIN_LEN:
            w = np.pad(w, (0, WIN_LEN - len(w)))
        else:
            w = w[:WIN_LEN]
        return w

    def predict(self, model_name: str,
                raw_window: np.ndarray) -> tuple[int, float]:
        """
        Returns (label_idx, confidence).
          label_idx : 0 = REST, 1 = CLICK
          confidence: 0.0 – 1.0
        """
        try:
            if model_name == "ET+RF Ensemble":
                feats = self._prep_features(raw_window)
                proba = self.ensemble.predict_proba(feats)[0]
                classes = list(self.ensemble.classes_)
                best = int(np.argmax(proba))
                raw_cls = classes[best]
                label = 1 if raw_cls == 5 else int(raw_cls != 0)
                return label, float(proba[best])

            elif model_name == "FNN":
                model, torch = self.fnn
                ft = torch.tensor(self._prep_features(raw_window),
                                  dtype=torch.float32).to(self.device)
                with torch.no_grad():
                    p = torch.softmax(model(ft), dim=1)[0].cpu().numpy()
                label = int(np.argmax(p))
                return label, float(p[label])

            elif model_name == "CNN":
                model, torch = self.cnn
                rt = torch.tensor(self._prep_raw(raw_window),
                                  dtype=torch.float32).unsqueeze(0).to(self.device)
                with torch.no_grad():
                    p = torch.softmax(model(rt), dim=1)[0].cpu().numpy()
                label = int(np.argmax(p))
                return label, float(p[label])

            elif model_name == "Hybrid CNN+FNN":
                model, torch = self.hybrid
                rt = torch.tensor(self._prep_raw(raw_window),
                                  dtype=torch.float32).unsqueeze(0).to(self.device)
                ft = torch.tensor(self._prep_features(raw_window),
                                  dtype=torch.float32).to(self.device)
                with torch.no_grad():
                    p = torch.softmax(model(rt, ft), dim=1)[0].cpu().numpy()
                label = int(np.argmax(p))
                return label, float(p[label])

            elif model_name == "Transformer":
                model, torch = self.transformer
                rt = torch.tensor(self._prep_raw(raw_window),
                                  dtype=torch.float32).unsqueeze(0).to(self.device)
                with torch.no_grad():
                    p = torch.softmax(model(rt), dim=1)[0].cpu().numpy()
                label = int(np.argmax(p))
                return label, float(p[label])

            elif model_name == "Transformer+FNN":
                model, torch = self.transformer_hybrid
                rt = torch.tensor(self._prep_raw(raw_window),
                                  dtype=torch.float32).unsqueeze(0).to(self.device)
                ft = torch.tensor(self._prep_features(raw_window),
                                  dtype=torch.float32).to(self.device)
                with torch.no_grad():
                    p = torch.softmax(model(rt, ft), dim=1)[0].cpu().numpy()
                label = int(np.argmax(p))
                return label, float(p[label])

        except Exception as e:
            print(f"[Predict Error] {model_name}: {e}")

        return 0, 0.5   # safe fallback
