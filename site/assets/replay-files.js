// Decide which local viewer handles the complete selection before reading any bytes.
export function replayFileKind(files, recordingPicker = false) {
  if (!files.length) return null;
  const gpxCount = files.filter((file) => /\.gpx$/i.test(file.name)).length;
  if (gpxCount && gpxCount !== files.length) {
    throw new Error("Open GPX recordings separately from JSON traces.");
  }
  if (recordingPicker && files.some((file) => /\.json$/i.test(file.name))) {
    throw new Error("Use the trace picker to open a JSON replay.");
  }
  const recording = recordingPicker || gpxCount > 0;
  if (recording && files.length > 2) throw new Error("Open one or two GPX recordings at a time.");
  if (!recording && files.length > 1) throw new Error("Open one JSON trace at a time.");
  const big = files.find((file) => file.size > 50e6);
  if (big) throw new Error(`${big.name} exceeds the 50 MB local replay file limit.`);
  return recording ? "recording" : "trace";
}

const TRACE_FORMAT = "follow-me-trace/1";
const MAKE_TRACE = "PYTHONPATH=src python3 -m follow_me.replay --json LOG.json > trace.json";

function validPosition(value) {
  return Number.isFinite(value?.x) && Number.isFinite(value.y) &&
    Number.isFinite(value.variance) && value.variance >= 0;
}

export function traceProblem(data) {
  if (!data || typeof data !== "object") return "This file is not a replay trace.";
  if (data.format !== TRACE_FORMAT) {
    if (Array.isArray(data.ticks)) return `This looks like a raw log, not a trace. Make a trace first: ${MAKE_TRACE}`;
    return `This file is not a replay trace (expected format ${TRACE_FORMAT}).`;
  }
  if (!Array.isArray(data.ticks) || data.ticks.length === 0) return "This trace has no ticks.";
  for (const [index, tick] of data.ticks.entries()) {
    const at = `Tick ${index + 1}`;
    if (!Number.isFinite(tick?.t) || !Array.isArray(tick.readings) || typeof tick.mode !== "string") {
      return `${at} needs a time, a readings list and a mode.`;
    }
    if (!["yaw", "forward", "climb"].every((axis) => Number.isFinite(tick.command?.[axis]))) {
      return `${at} needs numeric yaw, forward and climb command values.`;
    }
    for (const [i, reading] of tick.readings.entries()) {
      if (typeof reading?.source !== "string" || !validPosition(reading)) {
        return `${at}, reading ${i + 1} needs a source, finite coordinates and nonnegative variance.`;
      }
    }
    if (tick.estimate != null && !validPosition(tick.estimate)) {
      return `${at} has an invalid estimate position or variance.`;
    }
    if (tick.attention != null && (typeof tick.attention !== "object" || Array.isArray(tick.attention))) {
      return `${at} needs attention values keyed by source.`;
    }
  }
  return null;
}
