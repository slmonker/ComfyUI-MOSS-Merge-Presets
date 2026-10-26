from __future__ import annotations

from typing import Dict

NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}
WEB_DIRECTORY = "./web"


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
        "MOSS-Image Base + SFT layered merge. Connect Base to base_model and SFT to sft_model. "
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
        key_patches = sft_model.get_key_patches("diffusion_model.")
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


NODE_CLASS_MAPPINGS["MOSSMergePreset"] = MOSSMergePreset
NODE_DISPLAY_NAME_MAPPINGS["MOSSMergePreset"] = "MOSS Base+SFT Merge Preset"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
