# Changelog

## 1.0.2

- Added int8c/convrot Base + SFT compatibility.
- Quantization metadata keys are excluded from model patches.
- Quantized weights use ComfyUI's dequantize, interpolate, and requantize path.
- The merged model keeps the base model's quantization layout.

## 1.0.1

- Fixed the Base/SFT merge direction.
- `0` now correctly means pure Base and `1` means pure SFT.
- Preset values are now interpreted as SFT weights, matching the README and UI.
- Added a regression test for the merge direction.

## 1.0.0

- Initial public release.
- Added `Base-preserve`, `Balanced`, `SFT-detail`, and `Custom` modes.
- Added live per-layer merge information.
- Added English and Chinese documentation and test prompts.
