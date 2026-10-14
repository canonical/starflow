.. meta::
    :description: Reference checklist for releasing a Starcraft application, with separate steps for patch and minor releases.

.. _reference-app-release-checklist:

Application release checklist
=============================

Use these checklists for each application release. Work through one checklist in order,
and don't start a phase until the previous one is done. See `Quick links`_ at the end
of this page for the app-specific links that the steps refer to.

Starcraft follows the `OneFlow
<https://www.endoflineblog.com/oneflow-a-git-branching-model-and-workflow>`__ branching
model: a Git tag is a release, and supported releases are maintained in long-lived
``hotfix/*`` branches.


Patch release
-------------

A patch release carries a fix for a supported release, such as 1.3.1. Most of the work
happens on the ``hotfix/<major>.<minor>`` branch, and the release doesn't need a new
release notes page or documentation version.

This checklist assumes that all of the changes have already landed on the relevant hotfix
branch.

1. Update the lockfile. This means both updating the patch versions of any craft
   libraries and updating other libraries until they pass the security scanner.
2. Update the minor version release notes with a list of bugs that have been fixed in this
   patch version.
3. Once those have both landed, pull the latest ``hotfix/<major>.<minor>`` branch from
   GitHub and make a signed, annotated tag of the release:

   .. code-block:: bash

     BRANCH=hotfix/1.3  # Substitute the correct major.minor
     VERSION=1.3.1      # Substitute the correct major.minor.patch

     git fetch origin "$BRANCH"
     git checkout "$BRANCH"
     git pull

     git tag -sam "Release $VERSION" "$VERSION"
     git push origin "$VERSION"

4. Visit the Launchpad code page and re-import the project from GitHub.
5. Once the tag appears on the branch in Launchpad, find the correct Snap recipe from the
   project's snaps page.
   The recipe should be
   called something like ``charmcraft-4.x-next`` and automatically release to the candidate
   channel. Monitor it for a fresh build or, if not set to build automatically, request a
   build.
6. Monitor the builds until they have completed on all architectures. If one fails, you
   need to abandon this release, fix the build failure, and release a new patch version.
   The tag you've already pushed can't be reused, so the new release needs a new version.
7. Once the build has succeeded on all architectures, install the candidate snap and
   confirm that the fix works.
8. Write a message in the project's Matrix channel, announcing the patch release and
   linking to the relevant anchor on the release notes page.
9. Promote the build to the ``stable`` risk on the track for this major version.
10. If the release is for the current major version, promote it to the ``stable`` risk on the ``latest`` track too.
11. Check the snap's releases page to ensure the correct version is available on all architectures.
12. Check the Github releases page to ensure that this release exists on that page and that the correct
    release (possibly not this release if it's a patch for an older branch) is marked as "latest".
13. Branch off the ``hotfix/<major>.<minor>`` branch as ``work/hotfix-merge/<version>``,
    and merge ``main`` into it:

    .. code-block:: bash

      VERSION=1.3.1          # Substitute the correct major.minor.patch
      BRANCH=work/hotfix-merge/$VERSION

      git switch hotfix/1.3
      git switch -c "$BRANCH"
      git push -u origin "$BRANCH"

      git fetch origin
      git merge origin/main
      git push

14. Open a pull request from the ``work/hotfix-merge/<version>`` branch into ``main``,
    titled ``chore(merge): merge <release version> into main`` and labelled
    ``PR: Merge``.


Minor release
-------------

A minor release carries new features from ``main``, such as 1.4.0. It ends at the
``<major>.<minor>.0`` tag on ``main``, and it needs a release notes page and a new
documentation version.

This checklist assumes that all of relevant features have already landed on ``main``.

Release to candidate
~~~~~~~~~~~~~~~~~~~~

1. Ensure that all previous hotfix branches for the current major release have been merged
   to ``main``.
2. Update all dependencies using ``uv lock --update``
3. Create the release notes page for the minor version. List what changed, how to
   upgrade, and what breaks. Put the date on which you expect to promote the release to
   ``stable`` at the top of the page.
4. Propose the release notes page as a pull request on ``main``.
5. Once the release notes have landed, pull the latest ``main`` branch from GitHub and
   make a signed, annotated tag of the release:

   .. code-block:: bash

     VERSION=1.4.0          # Substitute the correct major.minor.patch

     git switch main
     git pull

     git tag -sam "Release $VERSION" "$VERSION"
     git push origin "$VERSION"

6. Create the ``hotfix/1.4`` branch from the tag. The Snap recipe builds from this
   branch, so it needs to exist before the sync in the next step. Later patches of this
   release branch from here.
7. Visit the Launchpad code page and re-import the project from GitHub.
8. Once the tag appears on the branch in Launchpad, find the correct Snap recipe from the
   project's snaps page.
   The recipe should be
   called something like ``charmcraft-4.x-next`` and automatically release to the
   ``candidate`` channel. Change the recipe to build from the ``hotfix/1.4`` branch,
   because it was still building from the previous hotfix branch.
   Monitor it for a fresh build or, if not set to build
   automatically, request a build.
9. Monitor the builds until they have completed on all architectures. If one fails, you
   need to abandon this release, fix the build failure, and release a new patch version.
   Other than the fact that you will be making a ``.1`` release, the release should follow
   the minor version release flow still.
10. Once the build has succeeded on all architectures, install the candidate snap and
    confirm that the new features work.
11. Create the documentation version on Read the Docs for the major version only (e.g.
    ``1`` for 1.4.0), sourced from the ``hotfix/1.4`` branch, and redirect the previous
    documentation versions to it. The calls for testing link to this version.
12. Write a call for testing in the project's Matrix channel. Announce the candidate
    release, ask for testing, and link to the release notes page.
13. Post the call for testing on the project's Discourse category, linking to the release
    notes page.
14. Leave the build on the ``candidate`` risk until the promotion date at the top of the
    release notes page. Treat that soak period as the last chance to catch regressions.

Promote to stable
~~~~~~~~~~~~~~~~~

1. Promote the build to the ``stable`` risk on the track for this major version and on the
   ``latest`` track.
2. Write a message in the project's Matrix channel announcing the release to
   ``stable``, and linking to the release notes page.
3. Edit the call for testing on Discourse to note that the release is now in ``stable``.
4. Check the snap's releases page to ensure the correct version is available on all architectures.
5. Check the Github releases page to ensure that this release exists on that page and is marked as "latest".


Quick links
-----------

Use these links to complete the release checklists above. Each app has its own tab.

.. tab-set::

    .. tab-item:: Charmcraft

        .. list-table::
            :header-rows: 1
            :widths: 25 75

            * - Link
              - URL
            * - Launchpad code page
              - `https://code.launchpad.net/charmcraft <https://code.launchpad.net/charmcraft>`__
            * - Snap recipes
              - `https://launchpad.net/charmcraft/+snaps <https://launchpad.net/charmcraft/+snaps>`__
            * - Next recipe, 4.x
              - `https://launchpad.net/~charmcraft-team/charmcraft/+snap/charmcraft-4.x-next <https://launchpad.net/~charmcraft-team/charmcraft/+snap/charmcraft-4.x-next>`__
            * - Next recipe, 3.x
              - `https://launchpad.net/~charmcraft-team/charmcraft/+snap/charmcraft-3.x-next <https://launchpad.net/~charmcraft-team/charmcraft/+snap/charmcraft-3.x-next>`__
            * - Matrix channel
              - `https://matrix.to/#/#charmhub-charmcraft:ubuntu.com <https://matrix.to/#/#charmhub-charmcraft:ubuntu.com>`__
            * - Discourse category
              - `https://discourse.charmhub.io/c/charmcraft/3 <https://discourse.charmhub.io/c/charmcraft/3>`__
            * - Release notes
              - `https://canonical.com/juju/docs/charmcraft/stable/release-notes/ <https://canonical.com/juju/docs/charmcraft/stable/release-notes/>`__
            * - Snap releases
              - `https://snapcraft.io/charmcraft/releases <https://snapcraft.io/charmcraft/releases>`__
            * - Github releases
              - `https://github.com/canonical/charmcraft/releases <https://github.com/canonical/charmcraft/releases>`__

    .. tab-item:: Debcraft

        .. list-table::
            :header-rows: 1
            :widths: 25 75

            * - Link
              - URL
            * - Launchpad code page
              - `https://code.launchpad.net/debcraft <https://code.launchpad.net/debcraft>`__
            * - Snap recipes
              - `https://launchpad.net/debcraft/+snaps <https://launchpad.net/debcraft/+snaps>`__
            * - Matrix channel
              - `https://matrix.to/#/#debcraft-development:ubuntu.com <https://matrix.to/#/#debcraft-development:ubuntu.com>`__
            * - Discourse category
              - `https://discourse.ubuntu.com/c/project/307 <https://discourse.ubuntu.com/c/project/307>`__
            * - Snap releases
              - `https://snapcraft.io/debcraft/releases <https://snapcraft.io/debcraft/releases>`__
            * - Github releases
              - `https://github.com/canonical/debcraft/releases <https://github.com/canonical/debcraft/releases>`__

    .. tab-item:: Imagecraft

        .. list-table::
            :header-rows: 1
            :widths: 25 75

            * - Link
              - URL
            * - Launchpad code page
              - `https://code.launchpad.net/imagecraft <https://code.launchpad.net/imagecraft>`__
            * - Snap recipes
              - `https://launchpad.net/imagecraft/+snaps <https://launchpad.net/imagecraft/+snaps>`__
            * - Candidate recipe
              - `https://launchpad.net/~canonical-starcraft/imagecraft/+snap/imagecraft-next <https://launchpad.net/~canonical-starcraft/imagecraft/+snap/imagecraft-next>`__
            * - Matrix channel
              - `https://matrix.to/#/#imagecraft:ubuntu.com <https://matrix.to/#/#imagecraft:ubuntu.com>`__
            * - Discourse category
              - `https://discourse.ubuntu.com/c/project/307 <https://discourse.ubuntu.com/c/project/307>`__
            * - Release notes
              - `https://documentation.ubuntu.com/imagecraft/stable/release-notes/ <https://documentation.ubuntu.com/imagecraft/stable/release-notes/>`__
            * - Snap releases
              - `https://snapcraft.io/imagecraft/releases <https://snapcraft.io/imagecraft/releases>`__
            * - Github releases
              - `https://github.com/canonical/imagecraft/releases <https://github.com/canonical/imagecraft/releases>`__

    .. tab-item:: Rockcraft

        .. list-table::
            :header-rows: 1
            :widths: 25 75

            * - Link
              - URL
            * - Launchpad code page
              - `https://code.launchpad.net/rockcraft <https://code.launchpad.net/rockcraft>`__
            * - Snap recipes
              - `https://launchpad.net/rockcraft/+snaps <https://launchpad.net/rockcraft/+snaps>`__
            * - Candidate recipe
              - `https://launchpad.net/~canonical-starcraft/+snap/rockcraft-candidate <https://launchpad.net/~canonical-starcraft/+snap/rockcraft-candidate>`__
            * - Matrix channel
              - `https://matrix.to/#/#rockcraft:ubuntu.com <https://matrix.to/#/#rockcraft:ubuntu.com>`__
            * - Discourse category
              - `https://discourse.ubuntu.com/c/project/rocks/rockcraft/118 <https://discourse.ubuntu.com/c/project/rocks/rockcraft/118>`__
            * - Release notes
              - `https://documentation.ubuntu.com/rockcraft/stable/release-notes/ <https://documentation.ubuntu.com/rockcraft/stable/release-notes/>`__
            * - Snap releases
              - `https://snapcraft.io/rockcraft/releases <https://snapcraft.io/rockcraft/releases>`__
            * - Github releases
              - `https://github.com/canonical/rockcraft/releases <https://github.com/canonical/rockcraft/releases>`__

    .. tab-item:: Snapcraft

        .. list-table::
            :header-rows: 1
            :widths: 25 75

            * - Link
              - URL
            * - Launchpad code page
              - `https://code.launchpad.net/snapcraft <https://code.launchpad.net/snapcraft>`__
            * - Snap recipes
              - `https://launchpad.net/snapcraft/+snaps <https://launchpad.net/snapcraft/+snaps>`__
            * - Candidate recipe
              - `https://launchpad.net/~sergiusens/+snap/snapcraft-candidate <https://launchpad.net/~sergiusens/+snap/snapcraft-candidate>`__
            * - Hotfix recipe, 9
              - `https://launchpad.net/~canonical-starcraft/snapcraft/+snap/snapcraft-9-hotfix <https://launchpad.net/~canonical-starcraft/snapcraft/+snap/snapcraft-9-hotfix>`__
            * - Hotfix recipe, 8
              - `https://launchpad.net/~canonical-starcraft/snapcraft/+snap/snapcraft-8-hotfix <https://launchpad.net/~canonical-starcraft/snapcraft/+snap/snapcraft-8-hotfix>`__
            * - Hotfix recipe, 7
              - `https://launchpad.net/~canonical-starcraft/snapcraft/+snap/snapcraft-7-hotfix <https://launchpad.net/~canonical-starcraft/snapcraft/+snap/snapcraft-7-hotfix>`__
            * - Matrix channel
              - `https://matrix.to/#/#snapcraft:ubuntu.com <https://matrix.to/#/#snapcraft:ubuntu.com>`__
            * - Discourse category
              - `https://forum.snapcraft.io/c/snapcraft/13 <https://forum.snapcraft.io/c/snapcraft/13>`__
            * - Release notes
              - `https://documentation.ubuntu.com/snapcraft/stable/release-notes/ <https://documentation.ubuntu.com/snapcraft/stable/release-notes/>`__
            * - Snap releases
              - `https://snapcraft.io/snapcraft/releases <https://snapcraft.io/snapcraft/releases>`__
            * - Github releases
              - `https://github.com/canonical/snapcraft/releases <https://github.com/canonical/snapcraft/releases>`__



