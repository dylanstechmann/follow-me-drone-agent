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
