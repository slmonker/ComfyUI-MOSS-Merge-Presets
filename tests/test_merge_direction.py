from pathlib import Path
import importlib.util
import sys
import tempfile
import types
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("moss_merge_presets", ROOT / "__init__.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FakeModel:
    def __init__(self):
        self.calls = []

    def clone(self):
        return self

    def get_key_patches(self, prefix):
        return {
            "diffusion_model.layers.0.proj.q.weight": [("sft-weight", None)],
        }

    def add_patches(self, patches, strength_patch, strength_model):
        self.calls.append((patches, strength_patch, strength_model))


class MergeDirectionTests(unittest.TestCase):
    def test_zero_is_base_and_one_is_sft(self):
        base = FakeModel()
        sft = FakeModel()
        node = module.MOSSMergePreset()

        node.merge(base, sft, "Custom", 0.0, "", **{
            field: 0.4 for field, _ in module.CUSTOM_FIELDS
        })
        _, strength_patch, strength_model = base.calls[-1]
        self.assertEqual(strength_patch, 0.0)
        self.assertEqual(strength_model, 1.0)

        node.merge(base, sft, "Custom", 1.0, "", **{
            field: 1.0 for field, _ in module.CUSTOM_FIELDS
        })
        _, strength_patch, strength_model = base.calls[-1]
        self.assertEqual(strength_patch, 1.0)
        self.assertEqual(strength_model, 0.0)

    def test_sft_detail_first_layer_uses_preset_sft_weight(self):
        base = FakeModel()
        sft = FakeModel()
        node = module.MOSSMergePreset()

        node.merge(base, sft, "SFT-detail", 1.0, "")
        _, strength_patch, strength_model = base.calls[-1]
        expected_sft = module.PRESETS["SFT-detail"]["layers.0."]
        self.assertAlmostEqual(strength_patch, expected_sft)
        self.assertAlmostEqual(strength_model, 1.0 - expected_sft)


class QuantizedCompatibilityTests(unittest.TestCase):
    def test_quant_metadata_keys_are_recognized(self):
        for key in (
            "diffusion_model.layers.0.proj.qkv.weight_scale",
            "diffusion_model.layers.0.proj.qkv.weight_scale_2",
            "diffusion_model.layers.0.proj.qkv.input_scale",
            "diffusion_model.layers.0.proj.qkv.pre_quant_scale",
            "diffusion_model.layers.0.proj.qkv.comfy_quant",
        ):
            self.assertTrue(module._is_quant_metadata_key(key))
        self.assertFalse(
            module._is_quant_metadata_key(
                "diffusion_model.layers.0.proj.qkv.weight"
            )
        )

    def test_quantized_extraction_falls_back_when_native_patch_fails(self):
        sentinel = {"diffusion_model.weight": ["quantized-patch"]}

        class QuantizedModel:
            def get_key_patches(self, _prefix):
                raise AttributeError("'Linear' object has no attribute 'weight_scale'")

        original = module._get_filtered_key_patches
        module._get_filtered_key_patches = lambda _model, _prefix: sentinel
        try:
            result = module._get_key_patches_compatible(
                QuantizedModel(), "diffusion_model."
            )
        finally:
            module._get_filtered_key_patches = original
        self.assertIs(result, sentinel)


class SaveNodeTests(unittest.TestCase):
    def test_filename_prefix_is_sanitized(self):
        self.assertEqual(
            module._sanitize_filename_prefix('my/merge:name?.safetensors'),
            "my_merge_name_",
        )
        self.assertEqual(module._sanitize_filename_prefix("  "), "moss_merge")

    def test_relative_output_directory_uses_comfyui_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            stub = types.ModuleType("folder_paths")
            stub.get_output_directory = lambda: temp_dir
            with mock.patch.dict(sys.modules, {"folder_paths": stub}):
                resolved = module._resolve_output_directory("moss_merged")
            self.assertEqual(str(resolved), str(Path(temp_dir) / "moss_merged"))

    def test_absolute_output_directory_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = str(Path(temp_dir) / "custom" / "moss")
            stub = types.ModuleType("folder_paths")
            stub.get_output_directory = lambda: temp_dir
            with mock.patch.dict(sys.modules, {"folder_paths": stub}):
                resolved = module._resolve_output_directory(target)
            self.assertEqual(str(resolved), target)

    def test_next_model_path_avoids_overwrite(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            first = module._next_model_path(directory, "merged", False)
            self.assertEqual(first.name, "merged.safetensors")
            first.touch()
            second = module._next_model_path(directory, "merged", False)
            self.assertEqual(second.name, "merged_00001_.safetensors")

    def test_save_node_is_registered(self):
        self.assertEqual(
            module.NODE_CLASS_MAPPINGS["MOSSMergeSaveModel"],
            module.MOSSMergeSaveModel,
        )
        self.assertEqual(
            module.NODE_DISPLAY_NAME_MAPPINGS["MOSSMergeSaveModel"],
            "MOSS Merge Save Model",
        )


if __name__ == "__main__":
    unittest.main()
