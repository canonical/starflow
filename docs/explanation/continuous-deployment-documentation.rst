.. meta::
    :description: Explanation of the continuous deployment process for documentation in Starcraft projects.


.. _explanation-continuous-deployment-documentation:

Continuous deployment for documentation
=======================================

This page explains the process of continuously deploying documentation in Starcraft apps
and libraries.


Deployment process
------------------

We publish documentation through a process that rides on top of our software development
and release process.


Main branch
~~~~~~~~~~~

.. image:: assets/continuous-deployment-main.svg
    :loading: lazy
    :alt: A Git tree history of the main branch, with a parallel history in a hotfix branch. Each commit to the main branch maps to a new publication for the latest version on Read the Docs. Documentation commits are represented in both histories, and publish separately until recombined in main.

All documentation changes in the repository's ``main`` branch are immediately deployed
to the ``latest`` documentation version on Read the Docs.

To make a documentation change for ``main``:

#. A contributor proposes a document.
#. Both technical authors review the document.
#. The continuous integration (CI) system runs the documentation test suite against the
   document. If product code was changed, the CI system runs the full test suite.
#. A technical author approves and merges the document.
#. Read the Docs publishes the update to ``https://<docs>/latest``


Current releases
~~~~~~~~~~~~~~~~

.. image:: assets/continuous-deployment-release.svg
    :loading: lazy
    :alt: A Git tree history of the release branch, in parallel with the history of the main branch. Each commit to the hotfix branch maps to a new publication for the hotfix's documentation version on Read the Docs. Documentation commits are represented in both histories, and publish separately until recombined in main.

All documentation changes in a current release's branch are immediately deployed to the
corresponding documentation version on Read the Docs. The process is largely the same as
with the ``main`` branch, with some differences in the branch controls.

Let's take the minor version 1.3 in a product as an example. To release 1.3:

#. The main engineer merges any changes on the ``main`` branch destined for the upcoming
   version.
#. The main engineer proposes the 1.3 release notes on the ``main`` branch.
#. The CI system runs all tests against the release notes.
#. A technical author reviews and approves the release notes.
#. The main engineer merges the release notes.
#. The main engineer tags the commit of the release notes, signifying in the source code
   that the version is released.
#. The main engineer `builds the release on the farm
   <https://discourse.canonical.com/t/release-process/626#p-722-import-the-code-on-launchpad-5>`__.
#. The main engineer creates the ``hotfix/1.3`` branch.
#. On Read the Docs, the TA creates documentation version 1.3, sourced from the
   ``hotfix/1.3`` branch.
#. The TA redirects the prior minor documentation versions to documentation version 1.3.
#. Read the Docs publishes the new version for that release, at ``https://<docs>/1.3``

To make a documentation change for 1.3:

#. A contributor proposes a document.
#. Both technical authors review the document.
#. The CI checks run the documentation checks against the document. If product code was
   changed, the CI system runs the full test suite.
#. A technical author approves and merges the document.
#. Read the Docs publishes the updated docs to ``https://<docs>/1.3``


Key factors
~~~~~~~~~~~

**Versioned documentation is deployed from hotfix branches.** The most important trait
of the process is that a current release's docs are republished with every commit. Every
commit to the release's hotfix branch republishes the documentation. They *do not*
*wait* for a new release. That way, improvements to the documentation are continuous.

If documentation is deployed parallel to the software's releases, why not merge to
``main`` and cherry pick changes to hotfix branches instead? First, because hotfixes
and ``main`` don't have feature parity. Documentation derived from product code, like
CLI references, can have incompatible differences. Second, the history between branches
isn't always linear. Patches and fixes are ported forward *and* backward. Resolving
these differences falls to the maintainers, and we don't want to burden them with more
work in rejoining histories.

**Technical authors approve and merge.** Documentation can only reach high velocity if
the review process is trim. Documentation is mechanically simple, and carries much less
risk than product code. Both benign and critical fixes in documents should be less
costly than a change to business logic like a new feature. Neither a correction to a
one-word typo nor a broken link deserve full engineering scrutiny. The technical authors
provide quality assurance and are accountable for documentation, so putting maintenance
burden on them doesn't reduce quality. In complex changes, they use their judgement and
ask engineers to review, if needed.

**Restricted tests for documents.** When a documentation change is proposed in a pull
request, the CI system runs only the documentation checks. Documents are only implicated
in the development test suite if they derive from the product source.


A difference in needs
---------------------

By design, the documentation process differs from the development process. Each activity
and the people carrying it out have different needs.


Development needs
~~~~~~~~~~~~~~~~~

Developers and users expect packaged software to be long-lasting and stable. Frequent
and irregular releases give users the perception that the software is of low quality,
and is potentially disruptive to their use. A careful approach, where software is
released infrequently and at a predictable rate, is best suited for packages. That's our
thinking behind how often and when we release our software.

To develop software stably and carefully, Starcraft practices the `OneFlow
<https://www.endoflineblog.com/oneflow-a-git-branching-model-and-workflow>`__ branching
style. In it, a Git tag signifies a software release. Supported releases are further
maintained inside long-lived hotfix branches, which protect concurrent releases from
regression because they separate the code into different channels. Since creating a tag
and spreading changes require a close understanding of the code and manual action by the
developer, these are suitable controls for our packaging mindset.


Documentation needs
~~~~~~~~~~~~~~~~~~~

Each Starcraft project publishes its documentation to its own live, public website.
Websites and web technologies operate on different principles than atomic packages. They
are live resources available at persistent addresses, their information must be
consistently accurate, and they must rarely, if ever, go offline for maintenance. This
means that for a given documentation site, readers expect the documentation to reliably
contain the latest and most accurate information available. It also means that fixes to
the site, to the documentation, shouldn't lag behind the software, and should never
require downtime.


Deployment, not delivery
------------------------

The requirements between delivering atomic software packages and up-to-date
documentation are in tension with each other. Software must release as infrequently as
possible, while its documentation must be updated the moment its information is out of
date.

We can say, then, that our software must provide **continuous delivery**, where it's
*capable* of deployment at any time with human intervention. Documentation, instead,
must practice **continuous deployment**, where every change to the documents *must* be
published automatically.


Results
-------

A good process benefits people. We want documentation deployment to be good for everyone
who uses, develops, and learns our software. Here are the particular results, written as
user statements, that we want it to provide.


Users
~~~~~

- When I go to ``https://<docs>/latest``, I see the latest documents from the ``main``
  branch.
- When I go to ``https://<docs>/1.3``, I see the latest documents for version 1.3.
- If there's a correction to the documents for version 1.3, I see it immediately in
  ``https://<docs>/1.3``.
- If there's a patch to version 1.3, the patch description is available at
  ``https://<docs>/1.3``.


Contributors
~~~~~~~~~~~~

- When I open a PR that only changes documentation, the CI system only runs the
  documentation checks.
- When reviewing my PR, I can expect that simple changes are merged within a day of
  receiving approval by the technical authors.
- In product code, like the CLI strings, I can link to ``https://<docs>/1.3``, and not
  worry about the patch number.


Engineers
~~~~~~~~~

- The process for deploying documentation is seamless and as automated as possible.
- The technical authors provide the majority of the documentation review.
- The technical authors can make corrections to the documentation without my oversight.


Technical authors
~~~~~~~~~~~~~~~~~

- The CI system takes no more than ten minutes to build and test a documentation
  proposal.
- When a member of another team opens a documentation pull request, I can review and
  merge it in as little time as possible.
- After both technical authors approve a documentation-only change that we have judged
  doesn't need an engineering review, I can merge it.
