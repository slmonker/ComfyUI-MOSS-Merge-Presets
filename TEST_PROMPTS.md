# MOSS Base + SFT Merge Test Prompts

Use the same seed and sampler settings when comparing `Base-preserve`, `Balanced`, and `SFT-detail`.

Recommended common settings:

- Resolution: `768x1024` for portraits, `1024x1024` for posters/products
- Seed: `42`
- Steps: `24-50`
- CFG: `3.5`
- Sampler: `er_sde`
- Scheduler: `simple`
- SLG: `single_layers=22`, `start=0.0`, `end=0.5`

Common negative prompt:

```text
nsfw, worst quality, bad anatomy, watermark, jpeg artifact
```

## 1. Female portrait: skin, hair, fabric, small text

```text
Cinematic half-body portrait of a young adult East Asian woman with short black hair, wearing a dark olive utility jacket, standing beside a rain-streaked window at dusk, soft warm practical light, natural skin texture, visible pores and fine hair strands, subtle freckles, realistic fabric wrinkles, shallow depth of field, 85mm lens, editorial photography. A small embroidered name patch on the jacket reads exactly "MOSS".
```

## 2. Male portrait: skin detail and dramatic lighting

```text
Close-up cinematic portrait of a middle-aged male blacksmith with a short beard and weathered skin, wearing a soot-stained linen shirt and a worn leather apron, standing in a dark forge lit by warm orange firelight, visible sweat, pores, scars, and individual beard hairs, realistic leather grain and metal dust, shallow depth of field, 85mm lens. A stamped leather label on the apron reads exactly "IRON".
```

## 3. Character design: costume and material separation

```text
Full-body character concept art of a female desert explorer with braided dark hair, wearing a layered sand-colored cloak, leather belts, brass goggles, and weathered boots, standing in front of a ruined stone gate at sunrise, realistic fabric weave, scratched metal, dust and sand particles, strong silhouettes, cinematic concept art, neutral gray-blue sky.
```

## 4. Product photography: reflections and label text

```text
Premium product photograph of a clear glass perfume bottle on a polished black stone plinth, amber liquid, rectangular label with the exact text "MOSS No.7", soft studio lighting from the left, crisp caustics, controlled reflections, fine mist droplets, subtle smoke in the background, luxury commercial photography, 100mm macro lens.
```

## 5. Typography poster: hierarchy and layout

```text
Minimal Swiss travel poster with a warm cream background, a deep blue geometric mountain range across the lower half, large bold uppercase title at the top reading exactly "NORTH", small dark text centered below reading exactly "ALPINE ROUTE 07", precise grid alignment, generous negative space, flat vector design, slight paper texture.
```

## 6. Complex interior: composition and multiple details

```text
Wide interior photograph of a narrow independent bookstore at night, tall wooden bookshelves, a rolling ladder, stacked books, warm reading lamps, rain-streaked front window, one barista working behind a small coffee counter, handwritten chalkboard reading exactly "NEW ARRIVALS", realistic wood grain, paper texture, glass reflections, natural perspective, editorial architectural photography.
```

## 7. Anime scene: style consistency and sign text

```text
Anime key visual of a quiet Tokyo alley after rain at night, two young adult characters walking away from the camera under clear umbrellas, reflective pavement, crowded shop signs, warm vending-machine light against cool blue shadows, detailed background, clean character silhouettes, cinematic composition. A large illuminated sign reads exactly "MOSS" and a smaller sign reads exactly "OPEN".
```

## 8. Material macro: glaze, droplets, and fine texture

```text
Macro photograph of a handcrafted ceramic teapot on a dark walnut table, warm golden window light from the left, fine glaze cracks, water droplets, irregular clay texture, soft shadow, shallow depth of field, realistic material response, 100mm macro lens, museum catalog photography.
```
