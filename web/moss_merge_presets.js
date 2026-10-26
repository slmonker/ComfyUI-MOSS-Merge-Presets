import { app } from "../../../scripts/app.js";

const NODE_CLASS = "MOSSMergePreset";
const NODE_TITLE = "MOSS Base+SFT Merge Preset";

const CUSTOM_FIELDS = [
  ["m_video_embedder", "video_embedder."],
  ["m_text_proj", "text_embedder.proj."],
  ["m_text_block0", "text_embedder.blocks.0."],
  ["m_text_block1", "text_embedder.blocks.1."],
  ["m_time", "time_embedding."],
  ["m_shared", "shared_block_modulation."],
  ...Array.from({ length: 42 }, (_, i) => [`m_L${String(i).padStart(2, "0")}`, `layers.${i}.`]),
  ["m_final_norm", "final_norm_video."],
  ["m_final_linear", "final_linear_video."],
  ["m_head", "video_head_modulation."],
];

function makePreset({ early, earlyLate, midEarly, midLate, lateEarly, lateLate, global, finalLinear }) {
  return {
    global,
    textBlocks: [Number((global * 0.8).toFixed(2)), Number((global * 0.8).toFixed(2))],
    time: Number((global * 1.2).toFixed(2)),
    layers: Array.from({ length: 42 }, (_, i) => {
      if (i <= 7) return early;
      if (i <= 13) return earlyLate;
      if (i <= 21) return midEarly;
      if (i <= 29) return midLate;
      if (i <= 35) return lateEarly;
      return lateLate;
    }),
    finalLinear,
  };
}

const PRESETS = {
  "Base-preserve": makePreset({ early: 0.08, earlyLate: 0.12, midEarly: 0.18, midLate: 0.28, lateEarly: 0.42, lateLate: 0.52, global: 0.12, finalLinear: 0.25 }),
  "Balanced": makePreset({ early: 0.15, earlyLate: 0.20, midEarly: 0.30, midLate: 0.45, lateEarly: 0.60, lateLate: 0.72, global: 0.20, finalLinear: 0.35 }),
  "SFT-detail": makePreset({ early: 0.25, earlyLate: 0.32, midEarly: 0.50, midLate: 0.65, lateEarly: 0.80, lateLate: 0.90, global: 0.30, finalLinear: 0.50 }),
};

function findWidget(node, name) {
  return node.widgets?.find((item) => item.name === name);
}

function setVisible(item, visible) {
  if (!item) return;
  item.hidden = !visible;
  item.options ??= {};
  item.options.hidden = !visible;
}

function scaled(value, strength) {
  return Math.min(1, Math.max(0, Number(value) * strength));
}

function fmt(value) {
  return Number(value).toFixed(2);
}

function valuesFor(node, preset) {
  const strength = Number(findWidget(node, "strength")?.value ?? 1);
  if (preset === "Custom") {
    const get = (name) => Number(findWidget(node, name)?.value ?? 0);
    return {
      strength,
      global: get("m_video_embedder"),
      textProj: get("m_text_proj"),
      textBlocks: [get("m_text_block0"), get("m_text_block1")],
      time: get("m_time"),
      shared: get("m_shared"),
      layers: Array.from({ length: 42 }, (_, i) => get(`m_L${String(i).padStart(2, "0")}`)),
      finalNorm: get("m_final_norm"),
      finalLinear: get("m_final_linear"),
      head: get("m_head"),
    };
  }

  const values = PRESETS[preset] ?? PRESETS.Balanced;
  return {
    strength,
    global: values.global,
    textProj: values.global,
    textBlocks: values.textBlocks,
    time: values.time,
    shared: values.global,
    layers: values.layers,
    finalNorm: values.global,
    finalLinear: values.finalLinear,
    head: values.global,
  };
}

function mergeInfoText(node, preset) {
  const values = valuesFor(node, preset);
  const s = values.strength;
  const layers = values.layers
    .map((value, i) => `L${String(i).padStart(2, "0")}=${fmt(scaled(value, s))}`)
    .join(" ");
  return [
    `${preset} | strength ${fmt(s)}`,
    `video_embedder=${fmt(scaled(values.global, s))}  text_proj=${fmt(scaled(values.textProj, s))}  text_blocks=${fmt(scaled(values.textBlocks[0], s))}/${fmt(scaled(values.textBlocks[1], s))}`,
    `time_embedding=${fmt(scaled(values.time, s))}  shared_modulation=${fmt(scaled(values.shared, s))}`,
    `layers: ${layers}`,
    `final_norm=${fmt(scaled(values.finalNorm, s))}  final_linear=${fmt(scaled(values.finalLinear, s))}  video_head=${fmt(scaled(values.head, s))}`,
  ].join("\n");
}

function syncNode(node) {
  const presetWidget = findWidget(node, "preset");
  const preset = presetWidget?.value ?? "Balanced";
  const isCustom = preset === "Custom";

  for (const [name] of CUSTOM_FIELDS) {
    setVisible(findWidget(node, name), isCustom);
  }

  const info = findWidget(node, "merge_info");
  if (info) info.value = mergeInfoText(node, preset);

  if (typeof node.computeSize === "function" && typeof node.setSize === "function") {
    const [width, height] = node.computeSize();
    node.setSize([Math.max(node.size?.[0] ?? 0, width, 440), height]);
  }
  node.setDirtyCanvas?.(true, true);
}

function installNode(node) {
  if (!node || node._mossMergePresetInstalled) return;
  const cls = node.comfyClass ?? node.constructor?.comfyClass ?? node.constructor?.nodeData?.name;
  if (cls !== NODE_CLASS && node.title !== NODE_TITLE) return;

  node._mossMergePresetInstalled = true;
  node.resizable = true;

  const monitored = [
    findWidget(node, "preset"),
    findWidget(node, "strength"),
    ...CUSTOM_FIELDS.map(([name]) => findWidget(node, name)),
  ].filter(Boolean);

  for (const item of monitored) {
    const previousCallback = item.callback;
    item.callback = function (...args) {
      const result = previousCallback?.apply(this, args);
      syncNode(node);
      return result;
    };
  }

  const previousConfigure = node.onConfigure;
  node.onConfigure = function (serialized) {
    const result = previousConfigure?.call(this, serialized);
    setTimeout(() => syncNode(this), 0);
    return result;
  };

  syncNode(node);
}

function currentGraph() {
  const candidates = [app.rootGraphRef?.value, app.canvas?.graph, app.rootGraph, app.graph].filter(Boolean);
  if (!candidates.length) return null;
  return candidates.sort((a, b) => (b?._nodes?.length ?? 0) - (a?._nodes?.length ?? 0))[0];
}

function currentNodes() {
  const graphs = [app.rootGraphRef?.value, app.canvas?.graph, app.rootGraph, app.graph].filter(Boolean);
  const seen = new Set();
  const nodes = [];
  for (const graph of graphs) {
    for (const node of (graph?._nodes ?? graph?.nodes ?? [])) {
      if (!seen.has(node)) { seen.add(node); nodes.push(node); }
    }
  }
  return nodes;
}

function scanGraph() {
  const graph = currentGraph();
  const nodes = currentNodes();
  for (const node of nodes) installNode(node);
}

app.registerExtension({
  name: "MOSS.MergePreset.DynamicLayers",
  beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData?.name !== NODE_CLASS) return;
    const previous = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function (...args) {
      const result = previous?.apply(this, args);
      installNode(this);
      return result;
    };
  },
  nodeCreated(node) {
    installNode(node);
  },
  loadedGraphNode(node) {
    installNode(node);
  },
});

scanGraph();
setInterval(scanGraph, 300);
