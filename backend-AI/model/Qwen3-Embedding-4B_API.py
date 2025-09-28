# -*- coding: utf-8 -*-
"""
Qwen3-Embedding-4B_API_LAST.py
A lightweight embedding HTTP server with micro-batching.

Requirements:
  - torch>=2.3.* (CUDA 12.x recommended)
  - transformers>=4.51.0
  - modelscope
  - flask

Optional:
  - flash-attn (FlashAttention-2)
  - bitsandbytes (4/8-bit quantization)

Features:
  - Embedding API (GET/POST), cosine similarity, rerank
  - Optional quantization: QUANT=none|bnb8|bnb4
  - Optional attention impl: ATTN_IMPL=flash_attention_2|sdpa|eager
  - Version-safe torch.set_float32_matmul_precision for torch>=2.9.0
  - Environment overrides for max length, micro-batch size, etc.
"""

import os
import sys
import time
import math
import threading
from collections import deque
from urllib.parse import unquote_plus
from typing import List, Dict, Any, Optional

import torch
import torch.nn.functional as F
from torch import Tensor
from flask import Flask, jsonify, request
from modelscope import AutoTokenizer, AutoModel

# Optional dependency: bitsandbytes (via Transformers integration)
try:
    from transformers import BitsAndBytesConfig
    _HAS_BNB = True
except Exception:
    _HAS_BNB = False

# -------------------------------
# Numeric / CUDA settings
# -------------------------------
torch.backends.cuda.matmul.allow_tf32 = True

def _version_ge(target: str) -> bool:
    """Return True if torch.__version__ >= target; robust without packaging."""
    tv = getattr(torch, "__version__", "0.0.0")
    # Prefer packaging.version if available
    try:
        from packaging import version as _pv
        return _pv.parse(tv) >= _pv.parse(target)
    except Exception:
        pass
    # Fallback: naive parse of first 3 numeric components
    def numtuple(v: str):
        parts = []
        for x in v.split("+")[0].split("."):
            if x.isdigit():
                parts.append(int(x))
            else:
                n = "".join(ch for ch in x if ch.isdigit())
                parts.append(int(n) if n else 0)
        while len(parts) < 3:
            parts.append(0)
        return tuple(parts[:3])
    return numtuple(tv) >= numtuple(target)

# Version-aware matmul precision (torch>=2.9 uses "highest")
if hasattr(torch, "set_float32_matmul_precision"):
    try:
        torch.set_float32_matmul_precision("highest" if _version_ge("2.9.0") else "high")
    except Exception:
        # Be tolerant on exotic builds
        pass

# -------------------------------
# Env config
# -------------------------------
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen3-Embedding-4B")

# Token truncation length
MAX_LENGTH = int(os.getenv("MAX_LENGTH", "160"))

# Micro-batching
BATCH_MAX_SIZE = int(os.getenv("BATCH_MAX_SIZE", "16"))
BATCH_TIMEOUT_MS = int(os.getenv("BATCH_TIMEOUT_MS", "8"))

# Defaults for embedding postprocess
DEFAULT_POOLING = os.getenv("DEFAULT_POOLING", "last")  # last | mean | cls
DEFAULT_NORMALIZE = os.getenv("DEFAULT_NORMALIZE", "true").lower() in ("1", "true", "yes", "y", "on")
DEFAULT_DIM = None  # Optional dimension truncation after pooling

# Attention / quantization options
ATTN_IMPL_ENV = os.getenv("ATTN_IMPL", "flash_attention_2").strip().lower()  # flash_attention_2 | sdpa | eager
REQUIRE_FLASH_ATTN = os.getenv("REQUIRE_FLASH_ATTN", "false").lower() in ("1", "true", "yes", "y", "on")
QUANT_MODE = os.getenv("QUANT", "none").strip().lower()  # none | bnb8 | bnb4
DTYPE_ENV = os.getenv("DTYPE", "auto").strip().lower()   # auto | bf16 | fp16 | fp32

CUDA_AVAILABLE = torch.cuda.is_available()
MODEL_MAIN_DEVICE = torch.device("cuda" if CUDA_AVAILABLE else "cpu")

app = Flask(__name__)

# -------------------------------
# Helpers
# -------------------------------
def _ensure_bool(val, default=True):
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ("1", "true", "yes", "y", "on")
    return bool(val)

def _ensure_int(val, default=None):
    if val is None:
        return default
    try:
        v = int(val)
        return v if v > 0 else default
    except Exception:
        return default

def _apply_instruction_prefix(text: str, instruction: Optional[str] = None, prefix: Optional[str] = None) -> str:
    t = (text or "").strip()
    if instruction:
        t = f"Instruction: {instruction}\nQuery: {t}"
    if prefix:
        t = f"{prefix}{t}"
    return t

def _masked_mean_pool(last_hidden_states: Tensor, attention_mask: Tensor) -> Tensor:
    mask = attention_mask.unsqueeze(-1).type_as(last_hidden_states)
    summed = (last_hidden_states * mask).sum(dim=1)
    counts = mask.sum(dim=1).clamp(min=1e-6)
    return summed / counts

def _last_token_pool(last_hidden_states: Tensor, attention_mask: Tensor) -> Tensor:
    # Heuristic: if left padding is used, the last position is the last token
    left_padding = (attention_mask[:, -1].sum() == attention_mask.shape[0])
    if left_padding:
        return last_hidden_states[:, -1]
    seq_lens = attention_mask.sum(dim=1) - 1
    bsz = last_hidden_states.shape[0]
    return last_hidden_states[torch.arange(bsz, device=last_hidden_states.device), seq_lens]

def _cls_pool(last_hidden_states: Tensor, attention_mask: Tensor) -> Tensor:
    if last_hidden_states.size(1) > 0:
        return last_hidden_states[:, 0]
    return _last_token_pool(last_hidden_states, attention_mask)

def _pool_single(p: str, lhs_row: Tensor, attn_row: Tensor) -> Tensor:
    p = (p or DEFAULT_POOLING).lower()
    if p == "mean":
        mask = attn_row.unsqueeze(-1).type_as(lhs_row)
        s = (lhs_row * mask).sum(dim=0)
        c = mask.sum(dim=0).clamp(min=1e-6)
        return s / c
    if p == "cls":
        return lhs_row[0] if lhs_row.shape[0] > 0 else lhs_row[-1]
    # default: last
    seq_len = int(attn_row.sum().item()) - 1
    seq_len = max(0, min(seq_len, lhs_row.shape[0] - 1))
    return lhs_row[seq_len]

def _postprocess(embs: Tensor, normalize: bool = True, dim: Optional[int] = None) -> Tensor:
    if dim is not None and dim > 0 and dim < embs.shape[1]:
        embs = embs[:, :dim].contiguous()
    if normalize:
        embs = F.normalize(embs, p=2, dim=1)
    return embs

def _cosine_similarity(a: Tensor, b: Tensor) -> Tensor:
    a = a.to(MODEL_MAIN_DEVICE, dtype=torch.float32)
    b = b.to(MODEL_MAIN_DEVICE, dtype=torch.float32)
    a = F.normalize(a, p=2, dim=1)
    b = F.normalize(b, p=2, dim=1)
    return a @ b.T

def _fa_available() -> bool:
    try:
        import flash_attn  # noqa: F401
        return True
    except Exception:
        return False

def _pick_dtype_from_env() -> torch.dtype:
    if DTYPE_ENV == "bf16":
        return torch.bfloat16
    if DTYPE_ENV == "fp16":
        return torch.float16
    if DTYPE_ENV == "fp32":
        return torch.float32
    # auto
    if CUDA_AVAILABLE and torch.cuda.is_bf16_supported():
        return torch.bfloat16
    if CUDA_AVAILABLE:
        return torch.float16
    return torch.float32

def _canonical_attn_impl() -> str:
    s = ATTN_IMPL_ENV
    if s in ("flash", "fa", "fa2", "flash_attn", "flashattention", "flashattention2"):
        s = "flash_attention_2"
    if s not in ("flash_attention_2", "sdpa", "eager"):
        s = "flash_attention_2"
    return s

# -------------------------------
# Decide attention impl & quantization
# -------------------------------
REQUESTED_ATTN = _canonical_attn_impl()
FLASH_AVAILABLE = _fa_available()

if REQUESTED_ATTN == "flash_attention_2" and not FLASH_AVAILABLE:
    if REQUIRE_FLASH_ATTN:
        print(
            "[FATAL] REQUIRE_FLASH_ATTN=1 but flash-attn is unavailable. "
            "Install: pip install flash-attn --no-build-isolation",
            file=sys.stderr,
        )
        sys.exit(1)
    print("[WARN] flash-attn not importable; falling back to SDPA.", file=sys.stderr)
    REQUESTED_ATTN = "sdpa"

if QUANT_MODE in ("bnb8", "bnb4") and not _HAS_BNB:
    print(f"[WARN] QUANT={QUANT_MODE} requested but bitsandbytes not installed; falling back to QUANT=none.", file=sys.stderr)
    QUANT_MODE = "none"

# -------------------------------
# Load tokenizer/model once
# -------------------------------
print("[BOOT] Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, padding_side="left", trust_remote_code=True)

torch_dtype = _pick_dtype_from_env()
print(f"[BOOT] Attn impl: {REQUESTED_ATTN} (flash_available={FLASH_AVAILABLE})")
print(f"[BOOT] Quant mode: {QUANT_MODE}")
print(f"[BOOT] Target dtype: {torch_dtype} (CUDA={CUDA_AVAILABLE}, bf16_supported={torch.cuda.is_bf16_supported() if CUDA_AVAILABLE else False})")

load_kwargs: Dict[str, Any] = {
    "torch_dtype": torch_dtype,
    "attn_implementation": REQUESTED_ATTN,  # flash_attention_2 | sdpa | eager
    "trust_remote_code": True,
}

MODEL_USES_DEVICE_MAP = False
if QUANT_MODE in ("bnb8", "bnb4"):
    # Build BitsAndBytes quantization config
    compute_dtype = torch.bfloat16 if torch_dtype == torch.bfloat16 else torch.float16
    if QUANT_MODE == "bnb8":
        bnb_cfg = BitsAndBytesConfig(load_in_8bit=True)
    else:
        bnb_cfg = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=compute_dtype,
        )
    load_kwargs["quantization_config"] = bnb_cfg
    load_kwargs["device_map"] = "auto"  # Let HF dispatch across available GPUs/CPU
    MODEL_USES_DEVICE_MAP = True

print(f"[BOOT] Loading model with attn_impl={REQUESTED_ATTN} ...")
try:
    model = AutoModel.from_pretrained(MODEL_NAME, **load_kwargs)
    if not MODEL_USES_DEVICE_MAP:
        model = model.to(MODEL_MAIN_DEVICE)
    model = model.eval()
except Exception as e:
    print(f"[FATAL] Failed to load model: {repr(e)}", file=sys.stderr)
    sys.exit(1)

print("[BOOT] Model ready.")

# -------------------------------
# Embedding core
# -------------------------------
@torch.inference_mode()
def _forward_last_hidden(processed_texts: List[str]):
    enc = tokenizer(
        processed_texts,
        padding=True,
        truncation=True,
        max_length=MAX_LENGTH,
        return_tensors="pt"
    )
    # With device_map, keep inputs on CPU; HF will shard/dispatch
    if not MODEL_USES_DEVICE_MAP:
        for k in enc:
            enc[k] = enc[k].to(MODEL_MAIN_DEVICE, non_blocking=True)

    out = model(input_ids=enc["input_ids"], attention_mask=enc["attention_mask"])
    last_hidden = out.last_hidden_state if hasattr(out, "last_hidden_state") else out[0]
    # Ensure attention mask device matches outputs
    attn_mask = enc["attention_mask"].to(last_hidden.device)
    return last_hidden, attn_mask

@torch.inference_mode()
def embed_texts(
    texts: List[str],
    pooling: str = DEFAULT_POOLING,
    normalize: bool = DEFAULT_NORMALIZE,
    out_dim: Optional[int] = DEFAULT_DIM,
    instruction: Optional[str] = None,
    prefix: Optional[str] = None,
) -> Tensor:
    processed = [_apply_instruction_prefix(str(t or ""), instruction, prefix) for t in texts]
    lhs, attn = _forward_last_hidden(processed)

    p = (pooling or DEFAULT_POOLING).lower()
    if p == "mean":
        pooled = _masked_mean_pool(lhs, attn)
    elif p == "cls":
        pooled = _cls_pool(lhs, attn)
    else:
        pooled = _last_token_pool(lhs, attn)

    embs = _postprocess(pooled, normalize=normalize, dim=out_dim)
    return embs

@torch.inference_mode()
def embed_texts_per_item(
    texts: List[str],
    poolings: List[str],
    normalizes: List[bool],
    out_dims: List[Optional[int]],
    instructions: List[Optional[str]],
    prefixes: List[Optional[str]],
) -> List[List[float]]:
    processed = [
        _apply_instruction_prefix(str(t or ""), instr, pref)
        for t, instr, pref in zip(texts, instructions, prefixes)
    ]
    lhs, attn = _forward_last_hidden(processed)

    vecs: List[Tensor] = []
    for i in range(len(texts)):
        pooled_i = _pool_single(poolings[i], lhs[i], attn[i])
        vec_i = pooled_i.unsqueeze(0)
        vec_i = _postprocess(vec_i, normalize=normalizes[i], dim=out_dims[i])
        vecs.append(vec_i.squeeze(0))

    return [v.detach().cpu().tolist() for v in vecs]

# -------------------------------
# Micro-batch queue
# -------------------------------
_request_queue = deque()
_queue_lock = threading.Lock()

def _batch_worker():
    while True:
        time.sleep(BATCH_TIMEOUT_MS / 1000.0)
        with _queue_lock:
            if not _request_queue:
                continue
            batch = []
            while _request_queue and len(batch) < BATCH_MAX_SIZE:
                batch.append(_request_queue.popleft())

        texts        = [item["text"] for item in batch]
        poolings     = [item["pooling"] for item in batch]
        normalizes   = [item["normalize"] for item in batch]
        out_dims     = [item["out_dim"] for item in batch]
        instructions = [item["instruction"] for item in batch]
        prefixes     = [item["prefix"] for item in batch]

        try:
            vecs = embed_texts_per_item(texts, poolings, normalizes, out_dims, instructions, prefixes)
            for v, item in zip(vecs, batch):
                item["vec"] = v
                item["evt"].set()
        except Exception as e:
            for item in batch:
                item["error"] = str(e)
                item["evt"].set()

threading.Thread(target=_batch_worker, daemon=True).start()

# -------------------------------
# Routes
# -------------------------------
@app.route("/", methods=["GET"])
def root():
    return jsonify({"ok": True, "model": MODEL_NAME})

@app.route("/health", methods=["GET"])
def health():
    # For device_map models, pick one param device for display only
    try:
        dev = next(model.parameters()).device
        dtype = str(next(model.parameters()).dtype)
    except StopIteration:
        dev = MODEL_MAIN_DEVICE
        dtype = str(torch_dtype)

    mem_total, mem_free = (0, 0)
    if CUDA_AVAILABLE:
        # torch.cuda.mem_get_info accepts device index or current device if None
        try:
            mem_free, mem_total = torch.cuda.mem_get_info(dev if isinstance(dev, int) else None)
        except Exception:
            # Best effort in multi-device setups
            mem_free, mem_total = torch.cuda.mem_get_info()

    return jsonify({
        "status": "ok",
        "queue_len": len(_request_queue),
        "device": str(dev),
        "dtype": dtype,
        "attn_impl": REQUESTED_ATTN,
        "flash_attention_requested": ATTN_IMPL_ENV in ("flash_attention_2","flash","fa","fa2","flashattention2","flash_attn"),
        "flash_attention_available": FLASH_AVAILABLE,
        "require_flash_attention": REQUIRE_FLASH_ATTN,
        "quant_mode": QUANT_MODE,
        "bf16_supported": torch.cuda.is_bf16_supported() if CUDA_AVAILABLE else False,
        "cuda_mem_total": mem_total,
        "cuda_mem_free": mem_free
    })

@app.route("/config", methods=["GET"])
def config():
    return jsonify({
        "model": MODEL_NAME,
        "max_length": MAX_LENGTH,
        "batch_max_size": BATCH_MAX_SIZE,
        "batch_timeout_ms": BATCH_TIMEOUT_MS,
        "defaults": {
            "pooling": DEFAULT_POOLING,
            "normalize": DEFAULT_NORMALIZE,
            "dim": DEFAULT_DIM,
        },
        "attn_impl": REQUESTED_ATTN,
        "flash_attention_requested": ATTN_IMPL_ENV in ("flash_attention_2","flash","fa","fa2","flashattention2","flash_attn"),
        "flash_attention_available": FLASH_AVAILABLE,
        "require_flash_attention": REQUIRE_FLASH_ATTN,
        "quant_mode": QUANT_MODE,
        "dtype": str(torch_dtype)
    })

@app.route("/metrics", methods=["GET"])
def metrics():
    try:
        dev = next(model.parameters()).device
        dtype = str(next(model.parameters()).dtype)
    except StopIteration:
        dev = MODEL_MAIN_DEVICE
        dtype = str(torch_dtype)

    mem_total, mem_free = (0, 0)
    if CUDA_AVAILABLE:
        try:
            mem_free, mem_total = torch.cuda.mem_get_info(dev if isinstance(dev, int) else None)
        except Exception:
            mem_free, mem_total = torch.cuda.mem_get_info()
    return jsonify({
        "queue_len": len(_request_queue),
        "device": str(dev),
        "dtype": dtype,
        "attn_impl": REQUESTED_ATTN,
        "flash_attention_available": FLASH_AVAILABLE,
        "quant_mode": QUANT_MODE,
        "cuda_mem_total": mem_total,
        "cuda_mem_free": mem_free
    })

# ---- GET single embedding with micro-batching ----
@app.route("/Qwen3-Embedding-4B/<path:text>", methods=["GET"])
def embed_get(text):
    raw_text = unquote_plus(text).strip()
    if not raw_text:
        return jsonify({"error": "empty text"}), 400

    pooling = request.args.get("pooling", DEFAULT_POOLING)
    normalize = _ensure_bool(request.args.get("normalize"), DEFAULT_NORMALIZE)
    out_dim = _ensure_int(request.args.get("dim"), DEFAULT_DIM)
    instruction = request.args.get("instruction", None)
    prefix = request.args.get("prefix", None)

    evt = threading.Event()
    req = {
        "text": raw_text,
        "evt": evt,
        "vec": None,
        "error": None,
        "pooling": pooling,
        "normalize": normalize,
        "out_dim": out_dim,
        "instruction": instruction,
        "prefix": prefix,
    }
    t0 = time.time()
    with _queue_lock:
        _request_queue.append(req)
    evt.wait()

    if req.get("error"):
        return jsonify({"error": req["error"]}), 500

    vec = req["vec"]
    elapsed_ms = math.floor((time.time() - t0) * 1000)
    return jsonify({
        "model": MODEL_NAME,
        "text": raw_text,
        "dim": len(vec),
        "pooling": pooling,
        "normalized": normalize,
        "elapsed_ms": elapsed_ms,
        "vector": vec,
        "note": "dim is post-truncation if provided (engineering down-projection)."
    })

# ---- POST batch embeddings (single forward) ----
@app.route("/Qwen3-Embedding-4B", methods=["POST"])
def embed_post():
    data = request.get_json(silent=True) or {}
    texts = data.get("texts", [])
    if not isinstance(texts, list) or not texts:
        return jsonify({"error": "JSON body must include non-empty 'texts' array"}), 400

    pooling = data.get("pooling", DEFAULT_POOLING)
    normalize = _ensure_bool(data.get("normalize"), DEFAULT_NORMALIZE)
    out_dim = _ensure_int(data.get("dim"), DEFAULT_DIM)
    instruction = data.get("instruction", None)
    prefix = data.get("prefix", None)

    t0 = time.time()
    vecs = embed_texts(
        [str(t or "").strip() for t in texts],
        pooling=pooling,
        normalize=normalize,
        out_dim=out_dim,
        instruction=instruction,
        prefix=prefix
    ).detach().cpu().tolist()
    elapsed_ms = math.floor((time.time() - t0) * 1000)
    return jsonify({
        "model": MODEL_NAME,
        "count": len(texts),
        "dim": len(vecs[0]),
        "pooling": pooling,
        "normalized": normalize,
        "elapsed_ms": elapsed_ms,
        "vectors": vecs,
        "note": "dim is post-truncation if provided (engineering down-projection)."
    })

# ---- Cosine similarity ----
@app.route("/similarity", methods=["POST"])
def similarity():
    data = request.get_json(silent=True) or {}
    a = data.get("a")
    b = data.get("b")
    if a is None or b is None:
        return jsonify({"error": "JSON must include 'a' and 'b' (text or vector)."}), 400

    pooling = data.get("pooling", DEFAULT_POOLING)
    normalize = _ensure_bool(data.get("normalize"), DEFAULT_NORMALIZE)
    out_dim = _ensure_int(data.get("dim"), DEFAULT_DIM)
    instruction = data.get("instruction", None)
    prefix = data.get("prefix", None)

    def _to_tensor(x):
        if isinstance(x, str):
            return embed_texts([x], pooling, normalize, out_dim, instruction, prefix)
        if isinstance(x, list):
            t = torch.tensor([x], dtype=torch.float32, device=MODEL_MAIN_DEVICE)
            # Always normalize for cosine; ignore out_dim for provided vectors
            return _postprocess(t, normalize=True, dim=None)
        return None

    va = _to_tensor(a)
    vb = _to_tensor(b)
    if va is None or vb is None:
        return jsonify({"error": "a/b must be string (text) or list[float] (vector)."}), 400

    score = float(_cosine_similarity(va, vb)[0, 0].detach().cpu().item())
    return jsonify({
        "model": MODEL_NAME,
        "similarity": score,
        "pooling": pooling,
        "normalized": True
    })

# ---- Rerank ----
@app.route("/rerank", methods=["POST"])
def rerank():
    data = request.get_json(silent=True) or {}
    query = data.get("query", "")
    cands = data.get("candidates", [])
    if not query or not isinstance(cands, list) or not cands:
        return jsonify({"error": "JSON must include non-empty 'query' and non-empty 'candidates' array."}), 400

    pooling = data.get("pooling", DEFAULT_POOLING)
    normalize = _ensure_bool(data.get("normalize"), DEFAULT_NORMALIZE)
    out_dim = _ensure_int(data.get("dim"), DEFAULT_DIM)
    instruction = data.get("instruction", None)
    prefix = data.get("prefix", None)

    with torch.inference_mode():
        qv = embed_texts([query], pooling, normalize, out_dim, instruction, prefix)
        dv = embed_texts([str(x) for x in cands], pooling, normalize, out_dim, instruction, prefix)
        sims = _cosine_similarity(qv, dv)[0].detach().cpu().tolist()

    paired = [{"index": i, "text": c, "score": float(s)} for i, (c, s) in enumerate(zip(cands, sims))]
    paired.sort(key=lambda x: x["score"], reverse=True)
    return jsonify({"model": MODEL_NAME, "results": paired})

# -------------------------------
# Entrypoint
# -------------------------------
if __name__ == "__main__":
    # For production consider:
    #   gunicorn -w 1 -k gthread -t 120 -b 0.0.0.0:7202 Qwen3-Embedding-4B_API_LAST:app
    app.run(host="0.0.0.0", port=7202, threaded=True)
