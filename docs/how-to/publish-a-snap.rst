.. meta::
    :description: How to publish a Starcraft application as a snap in the snap store.


.. _how-to-publish-a-snap:

Publish a Starcraft snap
========================

.. admonition::  Not All Crafts
    :class: tip

    While there are many ways to publish a snap, this is the process the Starcraft team uses.
    This process does not necessarily extend to non-craft snaps or even to craft snaps
    that are owned by other teams.

Snaps published by the Starcraft team are built on Launchpad using
:external+launchpad:ref:`snap recipes <build-snaps-in-launchpad>`. Each snap should be
published to at least the following channels:

- ``latest/edge``
- ``latest/candidate``
- ``latest/stable``

Once a craft reaches version 2.0, there should be a track representing each supported
major release.

Sync to Launchpad
-----------------

Before creating the recipe, the repository needs to be synced to Launchpad. To do this,
you must first `register the project <https://launchpad.net/projects/+new>`_. Ensure
that `~canonical-starcraft <https://launchpad.net/~canonical-starcraft>`_ is both the
maintainer and the driver. Next, set up the project's code repository to import from
the source on Github. In the end, visiting https://code.launchpad.net/yourcraft should
take you to the imported git repository. Compare to https://code.launchpad.net/snapcraft
if in doubt.

Register snap
-------------

If the snap is not yet registered, run ``snapcraft register <craft-name>`` in a terminal
to register it. When creating the recipe for the candidate channel, contact the store
team to have Canonical take ownership.

Publish to ``latest/edge``
--------------------------

All Starcraft apps should have their ``main`` branch published to the ``latest/edge``
channel when ``main`` changes. This is typically the first recipe that you create. Go
to the project page and click "Create snap package". Call the recipe "<yourcraft>-edge"
and give the starcraft team ownership of it. Select the main branch of the app's
repository and check all relevant processors for your app. In most cases, this will
be the :external+ubuntu:ref:`supported architectures <supported-architectures>` for the
latest Ubuntu LTS or a subset thereof.

Tick the "Automatically build when branch changes" box and the "Automatically upload to store"
box, and fill in the snap name. Leave the track empty and select the "Edge" risk.

After saving, test that the builds work correctly by manually requesting a build.
