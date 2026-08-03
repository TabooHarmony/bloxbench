import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { Type } from "typebox";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const outputPath = process.env.BLOX_SOURCE_OUTPUT;
if (!outputPath) {
  throw new Error("BLOX_SOURCE_OUTPUT is required");
}

const resolvedOutputPath = path.resolve(outputPath);
let writeCount = 0;

function errorCode(error: unknown): string | undefined {
  if (typeof error !== "object" || error === null || !("code" in error)) {
    return undefined;
  }
  const code = (error as { code?: unknown }).code;
  return typeof code === "string" ? code : undefined;
}

export default function (pi: ExtensionAPI) {
  pi.registerTool({
    name: "write_source",
    label: "write source",
    description:
      "Write the one final plain-text Luau source file for this run. Call exactly once with the complete source. Do not include Markdown fences or explanations.",
    parameters: Type.Object({
      content: Type.String({
        description: "Complete Luau source for the Roblox model.",
      }),
    }),
    async execute(_toolCallId, params) {
      if (writeCount !== 0) {
        return {
          content: [{ type: "text", text: "write_source may be called only once" }],
          isError: true,
          details: { reason: "duplicate_write" },
        };
      }

      const content = params.content;
      const bytes = Buffer.byteLength(content, "utf8");
      if (bytes === 0 || bytes > 200_000) {
        return {
          content: [{ type: "text", text: "source must be between 1 and 200000 UTF-8 bytes" }],
          isError: true,
          details: { reason: "invalid_size", bytes },
        };
      }
      if (content.includes("```")) {
        return {
          content: [{ type: "text", text: "source must not contain Markdown fences" }],
          isError: true,
          details: { reason: "markdown_fence" },
        };
      }

      await mkdir(path.dirname(resolvedOutputPath), { recursive: true });
      try {
        await writeFile(resolvedOutputPath, content, { encoding: "utf8", flag: "wx" });
      } catch (error) {
        if (errorCode(error) === "EEXIST") {
          return {
            content: [{ type: "text", text: "the fixed output path already exists" }],
            isError: true,
            details: { reason: "output_exists" },
          };
        }
        throw error;
      }
      writeCount = 1;
      return {
        content: [{ type: "text", text: "source written" }],
        details: {
          outputPath: resolvedOutputPath,
          bytes,
          writeCount,
        },
      };
    },
  });
}
