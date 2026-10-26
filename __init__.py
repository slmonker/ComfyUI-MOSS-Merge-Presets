from __future__ import annotations

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Dict

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}
WEB_DIRECTORY = "./web"

# int8c/convrot checkpoints expose extra quantization metadata next to each
# weight. These keys are not model parameters and must not be merged as if
# they were weights.
_QUANT_METADATA_SUFFIXES = (
    ".weight_scale",
    ".weight_scale_2",
    ".input_scale",
    ".pre_quant_scale",
    ".comfy_quant",
)


def _is_quant_metadata_key(key: str) -> bool:
    return key.endswith(_QUANT_METADATA_SUFFIXES)


def _get_filtered_key_patches(model, filter_prefix: str):
    """Return key patches for quantized models without quant metadata keys.

    ComfyUI's ModelPatcher.get_key_patches() walks every state-dict key. For
    int8c models that includes fields such as ``weight_scale`` and
    ``comfy_quant``, which are not module attributes and cause an
    AttributeError before the actual QuantizedTensor weights can be patched.

    The real weight entries remain QuantizedTensor objects. ComfyUI's patch
    path dequantizes them for interpolation and requantizes the result into
    the cloned base checkpoint's quantization layout.
    """
    import torch
    import comfy.model_patcher as model_patcher

    patches = {}
    for key in model.model_state_dict():
        if filter_prefix is not None and not key.startswith(filter_prefix):
            continue
        if _is_quant_metadata_key(key):
            continue

        try:
            weight, _, convert_func = model_patcher.get_key_weight(model.model, key)
        except AttributeError:
            # Other checkpoint-only metadata can have the same issue.
            continue
        if not isinstance(weight, torch.Tensor):
            continue

        backup = model.backup.get(key)
        hook_backup = model.hook_backup.get(key)
        if backup is not None:
            weight = backup.weight
        if hook_backup is not None:
            weight = hook_backup[0]
        if convert_func is None:
            convert_func = lambda value, **_: value

        patches[key] = [(weight, convert_func)] + model.patches.get(key, [])
    return patches


def _get_key_patches_compatible(model, filter_prefix: str):
    """Use native patch extraction, falling back for int8c/convrot models."""
    try:
        return model.get_key_patches(filter_prefix)
    except AttributeError as exc:
        logging.info(
            "MOSS merge: using quantized-model-compatible patch extraction (%s)",
            exc,
        )
        return _get_filtered_key_patches(model, filter_prefix)


def _resolve_output_directory(output_directory: str) -> Path:
    """Resolve an absolute path or a path relative to ComfyUI's output dir."""
    import folder_paths

    raw = (output_directory or "").strip().strip('"')
    if not raw:
        raw = folder_paths.get_output_directory()
    else:
        raw = os.path.expandvars(os.path.expanduser(raw))
        if not os.path.isabs(raw):
            raw = os.path.join(folder_paths.get_output_directory(), raw)
    return Path(os.path.abspath(raw))


def _sanitize_filename_prefix(filename_prefix: str) -> str:
    value = (filename_prefix or "").strip().strip('"')
    if value.lower().endswith(".safetensors"):
        value = value[: -len(".safetensors")]
    for char in '<>:"/\\|?*':
        value = value.replace(char, "_")
    value = "".join(char for char in value if ord(char) >= 32).strip(" .")
    return value or "moss_merge"


def _next_model_path(directory: Path, filename_prefix: str, overwrite: bool) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    if overwrite:
        return directory / f"{filename_prefix}.safetensors"

    candidate = directory / f"{filename_prefix}.safetensors"
    if not candidate.exists():
        return candidate
    counter = 1
    while True:
        candidate = directory / f"{filename_prefix}_{counter:05d}_.safetensors"
        if not candidate.exists():
            return candidate
        counter += 1


def _build_preset(*, early, early_late, mid_early, mid_late, late_early, late_late, global_scale, final_linear):
    weights: Dict[str, float] = {
        "video_embedder.": global_scale,
        "text_embedder.proj.": global_scale,
        "text_embedder.blocks.0.": round(global_scale * 0.8, 2),
        "text_embedder.blocks.1.": round(global_scale * 0.8, 2),
        "time_embedding.": round(global_scale * 1.2, 2),
        "shared_block_modulation.": global_scale,
    }
    for i in range(42):
        if i <= 7:
            value = early
        elif i <= 13:
            value = early_late
        elif i <= 21:
            value = mid_early
        elif i <= 29:
            value = mid_late
        elif i <= 35:
            value = late_early
        else:
            value = late_late
        weights[f"layers.{i}."] = value
    weights.update({
        "final_norm_video.": global_scale,
        "final_linear_video.": final_linear,
        "video_head_modulation.": global_scale,
    })
    return weights


# 0.0 keeps Base, 1.0 takes SFT for that component.
PRESETS = {
    "Base-preserve": _build_preset(
        early=0.08, early_late=0.12, mid_early=0.18, mid_late=0.28,
        late_early=0.42, late_late=0.52, global_scale=0.12, final_linear=0.25,
    ),
    "Balanced": _build_preset(
        early=0.15, early_late=0.20, mid_early=0.30, mid_late=0.45,
        late_early=0.60, late_late=0.72, global_scale=0.20, final_linear=0.35,
    ),
    "SFT-detail": _build_preset(
        early=0.25, early_late=0.32, mid_early=0.50, mid_late=0.65,
        late_early=0.80, late_late=0.90, global_scale=0.30, final_linear=0.50,
    ),
}

# UI field -> diffusion-model key prefix.
CUSTOM_FIELDS = [
    ("m_video_embedder", "video_embedder."),
    ("m_text_proj", "text_embedder.proj."),
    ("m_text_block0", "text_embedder.blocks.0."),
    ("m_text_block1", "text_embedder.blocks.1."),
    ("m_time", "time_embedding."),
    ("m_shared", "shared_block_modulation."),
]
CUSTOM_FIELDS += [(f"m_L{i:02d}", f"layers.{i}.") for i in range(42)]
CUSTOM_FIELDS += [
    ("m_final_norm", "final_norm_video."),
    ("m_final_linear", "final_linear_video."),
    ("m_head", "video_head_modulation."),
]

PRESET_ORDER = ["Base-preserve", "Balanced", "SFT-detail", "Custom"]
DEFAULT_CUSTOM = PRESETS["Balanced"]


class MOSSMergePreset:
    """One-click Base/SFT merge presets plus per-layer custom mode."""

    CATEGORY = "model/merging/moss"
    FUNCTION = "merge"
    RETURN_TYPES = ("MODEL",)
    RETURN_NAMES = ("MODEL",)
    OUTPUT_TOOLTIPS = ("Merged MOSS-Image model",)
    DESCRIPTION = (
        "MOSS-Image Base + SFT layered merge, including int8c/convrot models. "
        "Connect Base to base_model and SFT to sft_model. "
        "Select a preset to inspect its exact layer weights, or choose Custom to edit all 51 components."
    )

    @classmethod
    def INPUT_TYPES(cls):
        required = {
            "base_model": ("MODEL",),
            "sft_model": ("MODEL",),
            "preset": (PRESET_ORDER,),
            "strength": ("FLOAT", {
                "default": 1.0,
                "min": 0.0,
                "max": 1.25,
                "step": 0.01,
                "tooltip": "Global scale. 0 = pure Base, 1 = selected preset, 1.25 = stronger preset with each component clamped at 1.",
            }),
            "merge_info": ("STRING", {
                "default": "",
                "multiline": True,
                "tooltip": "Read-only display of effective per-layer merge weights after strength scaling.",
            }),
        }
        for field, prefix in CUSTOM_FIELDS:
            required[field] = ("FLOAT", {
                "default": float(DEFAULT_CUSTOM[prefix]),
                "min": 0.0,
                "max": 1.0,
                "step": 0.01,
                "tooltip": f"Custom merge weight for {prefix} (0=Base, 1=SFT).",
            })
        return {"required": required}

    def merge(self, base_model, sft_model, preset, strength, merge_info, **custom):
        if preset == "Custom":
            weights = {prefix: float(custom[field]) for field, prefix in CUSTOM_FIELDS}
        else:
            weights = PRESETS[preset]

        merged = base_model.clone()
        key_patches = _get_key_patches_compatible(sft_model, "diffusion_model.")
        ordered_weights = sorted(weights.items(), key=lambda item: len(item[0]), reverse=True)

        for key, patches in key_patches.items():
            unet_key = key[len("diffusion_model."):] if key.startswith("diffusion_model.") else key
            ratio = 0.0
            for prefix, value in ordered_weights:
                if unet_key.startswith(prefix):
                    ratio = value
                    break
            ratio = min(1.0, max(0.0, ratio * strength))
            # Public merge values are SFT weights: 0=Base, 1=SFT.
            # ComfyUI add_patches uses (strength_patch, strength_model), where
            # strength_model scales the cloned Base and strength_patch scales SFT.
            merged.add_patches({key: patches}, ratio, 1.0 - ratio)
        return (merged,)


class MOSSMergeSaveModel:
    """Save the merged MOSS diffusion model to a custom directory."""

    CATEGORY = "model/merging/moss"
    FUNCTION = "save"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("saved_path",)
    OUTPUT_TOOLTIPS = ("Absolute path to the saved .safetensors diffusion model.",)
    OUTPUT_NODE = True
    DESCRIPTION = (
        "Save a merged MOSS-Image diffusion MODEL as .safetensors. "
        "Use an absolute output directory, or a relative path under ComfyUI/output. "
        "The saved file loads with the Load Diffusion Model node."
    )

    @classmethod
    def INPUT_TYPES(cls):
        import folder_paths

        default_directory = os.path.join(folder_paths.get_output_directory(), "moss_merged")
        return {
            "required": {
                "model": ("MODEL",),
                "output_directory": ("STRING", {
                    "default": default_directory,
                    "multiline": False,
                    "tooltip": "Absolute path such as D:\\models\\moss, or a relative path under ComfyUI/output.",
                }),
                "filename_prefix": ("STRING", {
                    "default": "moss_merge",
                    "multiline": False,
                    "tooltip": "Output filename prefix. A counter is added if the file already exists.",
                }),
                "overwrite": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Overwrite the exact target file instead of adding a counter.",
                }),
                "save_metadata": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "Embed the workflow prompt and MOSS merge metadata when available.",
                }),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    def save(
        self,
        model,
        output_directory,
        filename_prefix,
        overwrite,
        save_metadata,
        prompt=None,
        extra_pnginfo=None,
    ):
        import comfy.sd

        output_dir = _resolve_output_directory(output_directory)
        prefix = _sanitize_filename_prefix(filename_prefix)
        final_path = _next_model_path(output_dir, prefix, bool(overwrite))
        temp_path = final_path.with_name(
            f".{final_path.stem}.{uuid.uuid4().hex}.part.safetensors"
        )

        metadata = {}
        if save_metadata:
            metadata["format"] = "pt"
            metadata["moss_merge.saved_by"] = "ComfyUI-MOSS-Merge-Presets"
            if prompt is not None:
                metadata["prompt"] = json.dumps(prompt, ensure_ascii=False)
            if extra_pnginfo is not None:
                for key, value in extra_pnginfo.items():
                    metadata[key] = json.dumps(value, ensure_ascii=False)

        try:
            comfy.sd.save_checkpoint(
                str(temp_path),
                model,
                metadata=metadata,
            )
            os.replace(temp_path, final_path)
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise

        size_mb = final_path.stat().st_size / (1024 * 1024)
        message = f"Saved MOSS model: {final_path} ({size_mb:.1f} MB)"
        logging.info(message)
        return {
            "ui": {"text": [message]},
            "result": (str(final_path),),
        }


NODE_CLASS_MAPPINGS["MOSSMergePreset"] = MOSSMergePreset
NODE_CLASS_MAPPINGS["MOSSMergeSaveModel"] = MOSSMergeSaveModel
NODE_DISPLAY_NAME_MAPPINGS["MOSSMergePreset"] = "MOSS Base+SFT Merge Preset"
NODE_DISPLAY_NAME_MAPPINGS["MOSSMergeSaveModel"] = "MOSS Merge Save Model"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
