import { describe, it, expect, vi, beforeEach } from "vitest";
import * as core from "@actions/core";
import * as exec from "@actions/exec";

vi.mock("@actions/core");
vi.mock("@actions/exec");
vi.mock("@actions/artifact");
vi.mock("fs/promises");

import {
  deriveSnapInfo,
  runScanner,
  readInputs,
  getSnapInfoField,
  type Inputs,
} from "../src/index.ts";

const BASE_INPUTS: Inputs = {
  snapFile: "/path/to/snap.snap",
  snapVersion: "1.0.0",
  productName: "my-snap",
  cycle: "25.04",
  releaseChannel: "stable",
};

describe("getSnapInfoField", () => {
  it("extracts the value for a given field", () => {
    expect(getSnapInfoField("name:      my-snap", "name")).toBe("my-snap");
  });

  it("extracts the correct field from a multi-line string", () => {
    const output = "name:      my-snap\nversion:   1.2.3\n";
    expect(getSnapInfoField(output, "version")).toBe("1.2.3");
  });

  it("returns an empty string when the field is not present", () => {
    expect(getSnapInfoField("version:   1.2.3", "name")).toBe("");
  });

  it("returns an empty string when the field has no value", () => {
    expect(getSnapInfoField("name:", "name")).toBe("");
  });
});

// Returns a mock implementation for exec.exec that feeds fake `snap info`
// output through the stdout listener.
function makeSnapInfoMock(name: string, version: string) {
  return vi
    .mocked(exec.exec)
    .mockImplementation(async (_cmd, _args, options) => {
      options?.listeners?.stdout?.(
        Buffer.from(`name:      ${name}\nversion:   ${version}\n`),
      );
      return 0;
    });
}

// Returns a mock implementation for exec.exec that returns the given exit
// codes for the `result` and `report` secscan-client subcommands, and 0
// for all others.
function makeSecscanclientMock(resultExitCode: number, reportExitCode = 0) {
  return vi
    .mocked(exec.exec)
    .mockImplementation(async (_cmd, args) => {
      if (args?.[1] === "result") return resultExitCode;
      if (args?.[1] === "report") return reportExitCode;
      return 0;
    });
}

describe("deriveSnapInfo", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("derives both product name and version when both are absent", async () => {
    makeSnapInfoMock("derived-snap", "2.0.0");
    const inputs: Inputs = { ...BASE_INPUTS, snapVersion: "", productName: "" };
    await deriveSnapInfo(inputs);
    expect(inputs.productName).toBe("derived-snap");
    expect(inputs.snapVersion).toBe("2.0.0");
  });

  it("derives only version when product name is already provided", async () => {
    makeSnapInfoMock("derived-snap", "2.0.0");
    const inputs: Inputs = {
      ...BASE_INPUTS,
      snapVersion: "",
      productName: "explicit-name",
    };
    await deriveSnapInfo(inputs);
    expect(inputs.productName).toBe("explicit-name");
    expect(inputs.snapVersion).toBe("2.0.0");
  });

  it("derives only product name when version is already provided", async () => {
    makeSnapInfoMock("derived-snap", "2.0.0");
    const inputs: Inputs = {
      ...BASE_INPUTS,
      snapVersion: "1.5.0",
      productName: "",
    };
    await deriveSnapInfo(inputs);
    expect(inputs.productName).toBe("derived-snap");
    expect(inputs.snapVersion).toBe("1.5.0");
  });

  it("throws when version cannot be derived from snap info output", async () => {
    vi.mocked(exec.exec).mockImplementation(async (_cmd, _args, options) => {
      // Output contains name but no version line
      options?.listeners?.stdout?.(Buffer.from("name:      my-snap\n"));
      return 0;
    });
    const inputs: Inputs = { ...BASE_INPUTS, snapVersion: "", productName: "" };
    await expect(deriveSnapInfo(inputs)).rejects.toThrow("snap-version");
  });

  it("throws when product name cannot be derived from snap info output", async () => {
    vi.mocked(exec.exec).mockImplementation(async (_cmd, _args, options) => {
      // Output contains version but no name line
      options?.listeners?.stdout?.(Buffer.from("version:   1.0.0\n"));
      return 0;
    });
    const inputs: Inputs = { ...BASE_INPUTS, snapVersion: "", productName: "" };
    await expect(deriveSnapInfo(inputs)).rejects.toThrow("product-name");
  });
});

describe("runScanner", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("resolves on exit code 0 (no CVEs)", async () => {
    makeSecscanclientMock(0);
    await expect(
      runScanner("blackduck", BASE_INPUTS, "/tmp/tokens", "/tmp/results"),
    ).resolves.toBeUndefined();
  });

  it("throws on exit code 1 (processing error, lower boundary)", async () => {
    makeSecscanclientMock(1);
    await expect(
      runScanner("blackduck", BASE_INPUTS, "/tmp/tokens", "/tmp/results"),
    ).rejects.toThrow();
  });

  it("throws on exit code 99 (processing error, upper boundary)", async () => {
    makeSecscanclientMock(99);
    await expect(
      runScanner("blackduck", BASE_INPUTS, "/tmp/tokens", "/tmp/results"),
    ).rejects.toThrow();
  });

  it("resolves on exit code 100", async () => {
    makeSecscanclientMock(100);
    await expect(
      runScanner("blackduck", BASE_INPUTS, "/tmp/tokens", "/tmp/results"),
    ).resolves.toBeUndefined();
  });

  it("resolves on exit code 101 (unnecessary CVE exclusions)", async () => {
    makeSecscanclientMock(101);
    await expect(
      runScanner("blackduck", BASE_INPUTS, "/tmp/tokens", "/tmp/results"),
    ).resolves.toBeUndefined();
  });

  it("resolves on exit code 102 (CVEs found)", async () => {
    makeSecscanclientMock(102);
    await expect(
      runScanner("blackduck", BASE_INPUTS, "/tmp/tokens", "/tmp/results"),
    ).resolves.toBeUndefined();
  });

  it("does not throw on a non-zero report exit code", async () => {
    makeSecscanclientMock(0, 1);
    await expect(
      runScanner("blackduck", BASE_INPUTS, "/tmp/tokens", "/tmp/results"),
    ).resolves.toBeUndefined();
  });
});

describe("readInputs", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("does not call snap info when all inputs are explicitly provided", async () => {
    vi.mocked(core.getInput).mockImplementation((name) => {
      const values: Record<string, string> = {
        "snap-file": "/path/to/snap.snap",
        "snap-version": "1.0.0",
        "product-name": "my-snap",
        "cycle": "25.04",
        "release-channel": "stable",
      };
      return values[name] ?? "";
    });
    await readInputs();
    expect(exec.exec).not.toHaveBeenCalledWith(
      "snap",
      expect.anything(),
      expect.anything(),
    );
  });
});
