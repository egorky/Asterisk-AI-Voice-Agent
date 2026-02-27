export function sanitizeConfigForSave(config: any): any {
  if (!config || typeof config !== "object") return config;

  const out: any = { ...config };

  // Pipelines: tools are configured per-context only; pipelines.*.tools is deprecated.
  if (out.pipelines && typeof out.pipelines === "object") {
    const nextPipelines: any = Array.isArray(out.pipelines) ? {} : { ...out.pipelines };
    for (const [name, pipeline] of Object.entries(out.pipelines)) {
      if (pipeline && typeof pipeline === "object" && !Array.isArray(pipeline)) {
        const { tools: _legacyTools, ...rest } = pipeline as any;
        nextPipelines[name] = rest;
      } else {
        nextPipelines[name] = pipeline;
      }
    }
    out.pipelines = nextPipelines;
  }

  return out;
}

/**
 * Serialize a config object to YAML preserving UTF-8 characters (ñ, á, é, etc.)
 * js-yaml v4 by default may escape non-ASCII chars; noCompatMode prevents that.
 */
import yaml from 'js-yaml';
export function yamlDump(data: any): string {
  return yaml.dump(data, { noRefs: true, lineWidth: -1, noCompatMode: true, allowUnicode: true } as any);
}
