.. meta::
    :description: How to configure staging GitHub Actions variables and secrets for the Starcraft team's Ubuntu One staging account.

.. _how-to-github-secrets-setup:

Set up GitHub Actions variables and secrets for staging
=======================================================

This guide explains how to configure the credentials for the Starcraft team's Ubuntu One staging account used by CI workflows.

Prerequisites
-------------

Before starting, ensure you have:

* Administrator access to the target GitHub repository.
* Access to the corporate password manager.
* Access to the **Starcraft Shared Accounts** collection.



Retrieve the Starcraft team's Ubuntu One staging account credentials
--------------------------------------------------------------------

1. In the corporate password manager, locate the **Starcraft Shared Accounts**
   collection. Open the **Ubuntu SSO Staging** login.
2. Confirm the username is ``starcraft-team+staging-sso@groups.canonical.com``.
3. Copy the login password when you are ready to paste it into GitHub.

Create the required GitHub entries
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add one Actions variable and one Actions secret to match the workflow configuration.

1. In the repository's settings, under **Secrets and variables** > **Actions**, open the **Variables** tab.
2. Create a variable named ``STAGING_SSO_USERNAME`` with value
   ``starcraft-team+staging-sso@groups.canonical.com``.
3. Open the **Secrets** tab.
4. Create a secret named ``STAGING_SSO_PASSWORD`` with the password from the Starcraft
   team's Ubuntu One staging account.

Configure workflow access
~~~~~~~~~~~~~~~~~~~~~~~~~

If credentials fail to load during a workflow run, check:

   * ``vars.STAGING_SSO_USERNAME`` exists.
   * ``secrets.STAGING_SSO_PASSWORD`` exists.
   * The names match the workflow YAML exactly.

Use these values in a workflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This example shows how to pass the variable and secret into a reusable workflow and expose
them as environment variables for tests:

.. code-block:: yaml

    jobs:
      test:
        uses: canonical/starflow/.github/workflows/test-python.yaml@main
        secrets:
          secret-1: ${{ secrets.STAGING_SSO_PASSWORD }}
        with:
          extra-env-vars: |
            STAGING_SSO_USERNAME=${{ vars.STAGING_SSO_USERNAME }}
            STAGING_SSO_PASSWORD=$SECRET_1
