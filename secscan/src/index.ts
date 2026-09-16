import * as core from "@actions/core";
import * as exec from "@actions/exec";
import * as artifact from "@actions/artifact";
import { mkdir, readdir, rm, writeFile } from "fs/promises";
import { join } from "path";

const SUPPORTED_SCANNERS = ["blackduck", "trivy", "osv"] as const;
const SCANNER_OUTPUT_FORMAT = {
  blackduck: "json",
  trivy: "html",
  osv: "txt",
} as const;

// Mapping of internal variable names to their key name in a workflow file.
const INPUT_MAPPING = {
  snapFile: { wfName: "snap-file", required: true },
  snapVersion: { wfName: "snap-version", required: false },
  productName: { wfName: "product-name", required: false },
  cycle: { wfName: "cycle", required: true },
  releaseChannel: { wfName: "release-channel", required: true },
} as const;

// Declares Inputs as an object with fields exactly matching those of INPUT_MAPPING's keys,
// and each field is a string.
export type Inputs = Record<keyof typeof INPUT_MAPPING, string>;

export function getSnapInfoField(output: string, field: string): string {
  return (
    output.match(new RegExp(`^${field}:\\s+(.+)$`, "m"))?.[1]?.trim() ?? ""
  );
}

export async function deriveSnapInfo(inputs: Inputs): Promise<void> {
  let capturedOutput = "";
  // Callback to accumulate command output into resultOutput
  const listenerCallback = (data: Buffer) => {
    capturedOutput += data.toString();
  };
  await exec.exec("snap", ["info", inputs.snapFile], {
    listeners: { stdout: listenerCallback, stderr: listenerCallback },
  });

  const name = getSnapInfoField(capturedOutput, "name");
  const version = getSnapInfoField(capturedOutput, "version");

  inputs.productName = inputs.productName || name;
  inputs.snapVersion = inputs.snapVersion || version;

  if (inputs.snapVersion === "") {
    throw new Error(
      "Snap version could not be derived from the input snap file; provide an explicit version with 'snap-version'.",
    );
  }
  if (inputs.productName === "") {
    throw new Error(
      "Product name could not be derived from the input snap file; provide an explicit name with 'product-name'.",
    );
  }
}

export async function readInputs(): Promise<Inputs> {
  // Dynamically build an Inputs object, passing the workflow-formatted name into getInput
  // and assigning it to the internal name on Inputs
  const inputs = Object.fromEntries(
    Object.entries(INPUT_MAPPING).map(([internalName, attrs]) => [
      internalName,
      core.getInput(attrs.wfName, { required: attrs.required }),
    ]),
  ) as Inputs;

  if (inputs.snapVersion === "" || inputs.productName === "") {
    await deriveSnapInfo(inputs);
  }

  return inputs;
}

export async function runScanner(
  scanner: (typeof SUPPORTED_SCANNERS)[number],
  inputs: Inputs,
  tokensDir: string,
  resultsDir: string,
): Promise<void> {
  const tokenFile = join(tokensDir, `${scanner}-token.txt`);
  const scannerResultsDir = join(resultsDir, scanner);
  await mkdir(scannerResultsDir, { recursive: true });

  await exec.exec("secscan-client", [
    "--batch",
    "submit",
    "--scanner",
    scanner,
    "--type",
    "package",
    "--format",
    "snap",
    "--token",
    tokenFile,
    "--ssdlc-product-name",
    inputs.productName,
    "--ssdlc-product-version",
    inputs.snapVersion,
    "--ssdlc-product-channel",
    inputs.releaseChannel,
    "--ssdlc-cycle",
    inputs.cycle,
    inputs.snapFile,
  ]);

  await exec.exec("secscan-client", ["--batch", "wait", "--token", tokenFile]);

  let capturedOutput = "";
  // Callback to accumulate command output into resultOutput
  const listenerCallback = (data: Buffer) => {
    capturedOutput += data.toString();
  };

  let exitCode = await exec.exec(
    "secscan-client",
    ["--batch", "result", "--token", tokenFile],
    {
      listeners: {
        stdout: listenerCallback,
        stderr: listenerCallback,
      },
      ignoreReturnCode: true,
    },
  );

  // Special explicit handling of the return code.
  //
  // "0" - success, no CVEs
  // "1-99" - processing error (treat as failure)
  // "101" - success with unnecessary CVE ignores
  // anything else - CVEs found, treat as success for this workflow
  if (exitCode >= 1 && exitCode <= 99) {
    core.error(capturedOutput);
    throw new Error(`Scanner ${scanner} failed with exit code ${exitCode}`);
  }

  const resultFile = join(scannerResultsDir, `${scanner}_result.txt`);
  const resultPromise = writeFile(resultFile, capturedOutput);

  capturedOutput = "";
  exitCode = await exec.exec(
    "secscan-client",
    ["--batch", "report", "--token", tokenFile],
    {
      listeners: {
        stdout: listenerCallback,
        stderr: listenerCallback,
      },
      ignoreReturnCode: true,
    },
  );

  if (exitCode !== 0) {
    core.error(capturedOutput);
  }

  const reportExt = SCANNER_OUTPUT_FORMAT[scanner];
  const reportFile = join(scannerResultsDir, `${scanner}_report.${reportExt}`);
  await writeFile(reportFile, capturedOutput);
  await resultPromise;
}

async function run(): Promise<void> {
  // $RUNNER_TEMP is set by the GH runners, no need to handle the "undefined" case here
  const runnerTemp = process.env.RUNNER_TEMP as string;

  // mkdir -p $RUNNER_TEMP/secscan-{tokens,results}
  const tokensDir = join(runnerTemp, "secscan-tokens");
  await mkdir(tokensDir, {
    recursive: true,
  });
  const resultsDir = join(runnerTemp, "secscan-results");
  await mkdir(resultsDir, {
    recursive: true,
  });

  try {
    await runInner(tokensDir, resultsDir);
  } catch (error) {
    core.setFailed(error instanceof Error ? error.message : String(error));
  } finally {
    await rm(tokensDir, { recursive: true });
  }
}

async function runInner(tokensDir: string, resultsDir: string): Promise<void> {
  const inputs = await readInputs();
  await exec.exec("sudo", ["snap", "install", "canonical-secscan-client"]);
  await exec.exec("sudo", [
    "snap",
    "connect",
    "canonical-secscan-client:home",
    ":home",
  ]);

  const scannerResults = await Promise.allSettled(
    SUPPORTED_SCANNERS.map((scanner) =>
      runScanner(scanner, inputs, tokensDir, resultsDir),
    ),
  );

  const failures = scannerResults.flatMap((result, i) =>
    result.status === "rejected"
      ? [`${SUPPORTED_SCANNERS[i]}: ${result.reason}`]
      : [],
  );

  if (failures.length > 0) {
    const summary = failures.join("\n  ");
    core.setFailed(summary);
  }

  // If at least one scanner passed, upload its output
  if (failures.length !== SUPPORTED_SCANNERS.length) {
    const files = (await readdir(resultsDir, { recursive: true })).map((f) =>
      join(resultsDir, f),
    );
    await new artifact.DefaultArtifactClient().uploadArtifact(
      "secscan-results",
      files,
      resultsDir,
    );
    core.setOutput("secscan-results", resultsDir);
  }
}

if (import.meta.url === `file://${process.argv[1]}`) {
  run();
}
