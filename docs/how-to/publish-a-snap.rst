.. meta::
    :description: How to publish a Starcraft app as a snap in the snap store.


.. _how-to-publish-a-starcraft-snap:

Publish a Starcraft snap
========================

Craft apps are packed into snaps and published to the Snap Store according to
the process in this guide. Our process doesn't apply to other apps or snaps
maintained by other teams.

We build our snaps on Launchpad with
:external+launchpad:ref:`snap recipes <build-snaps-in-launchpad>`. Configure a recipe for
``latest/edge``. For apps that already use ``latest/candidate`` and ``latest/stable``,
candidate builds are also managed through recipes, while validated revisions are promoted to
stable directly in the Snap Store.

Once a craft app reaches version 2.0, there should be a track representing each
supported major release.

Publishing to these channels is managed through snap recipes on Launchpad. When
setting up a new app, you only need to create the recipe for ``latest/edge``.
The ``candidate`` and ``stable`` channels are handled later during the release
process.

Initialize the project on Launchpad
-----------------------------------

If the app is new, you must register and sync it on Launchpad before you can
publish it.

First, `register the project <https://launchpad.net/projects/+new>`__. Make
`~canonical-starcraft <https://launchpad.net/~canonical-starcraft>`__ both the
maintainer and the driver.

Next, set the project to import from the source on GitHub.

If successful, https://code.launchpad.net/<yourcraft> should open the imported Git
repository. If it isn't working, compare your project to the settings and
results in https://code.launchpad.net/snapcraft.

Register the snap
-----------------

If the snap is not yet registered, run ``snapcraft register <craft-name>`` in a terminal
to register it. When creating the recipe for the candidate channel, contact the store
team to have Canonical take ownership.

Publish to ``latest/edge``
--------------------------

The ``main`` branch of all craft apps should publish to the ``latest/edge``
channel. This is typically the first recipe that you create.

Go to the project page on Launchpad and click **Create snap package**. Name the recipe
**<yourcraft>-edge** and give the Starcraft team ownership of it.

Select the main branch of the app's repository and check all relevant processors for
your app. In most cases, this will be the :external+ubuntu:ref:`supported architectures
<supported-architectures>` for the latest Ubuntu LTS, or a subset of it.

Select **Automatically build when branch changes** and **Automatically upload to store**,
and enter the snap name. Leave the track empty and select the **Edge** risk.

After saving, test that the builds work correctly by manually requesting a build.


Candidate and stable channels
-----------------------------

These instructions apply only to apps that already have ``latest/candidate`` and
``latest/stable`` channels. They aren't part of the initial debcraft setup. Create the
candidate recipe when preparing a release:

- **Candidate**: Create a recipe for ``latest/candidate`` (such as
  **<yourcraft>-candidate**) when preparing a release, pointing to the release or
  hotfix branch. Contact the store team to ensure Canonical owns the snap before
  publishing candidate builds.
- **Stable**: Do not create a separate build recipe for ``latest/stable``. Instead,
  after testing and validating a revision in ``latest/candidate``, promote that
  revision to ``latest/stable`` directly in the Snap Store.
