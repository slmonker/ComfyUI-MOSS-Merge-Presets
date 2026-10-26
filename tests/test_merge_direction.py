from pathlib import Path
import importlib.util
import unittest

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


if __name__ == "__main__":
    unittest.main()
