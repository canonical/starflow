import * as core from '@actions/core';

async function run(): Promise<void> {
  try {
    const myInput = core.getInput('my-input', { required: true });
    core.info(`Hello from example-action: ${myInput}`);
  } catch (error) {
    if (error instanceof Error) {
      core.setFailed(error.message);
    }
  }
}

run();
