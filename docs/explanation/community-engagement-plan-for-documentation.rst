.. _explanation-community-engagement-plan-for-documentation:

Community engagement plan for documentation
===========================================

This plan defines our objectives and approach to providing healthy and reliable
engagement with documentation activity in our projects' communities.


Mission and objectives
----------------------

Our mission is to `bring free software to the widest audience
<https://ubuntu.com/community/ethos/mission>`_. Every team member will help realize the
documentation side of this mission with these objectives in mind:

- Be upstanding and involved citizens in our projects' communities.
- Be responsive and accountable to the communities' documentation needs.
- Provide hands-on support to documentation contributors and help them succeed.
- Be an exemplary project in the `Canonical Open Documentation Academy (CODA)
  <https://documentation.academy>`_.


Responsibilities
----------------

Community members engage with us throughout our official communication channels and
spaces on Matrix, Discourse, and GitHub. We also host live workshops and community
hours.

To remain accountable and responsive to members' engagement with the documentation, our
engineers and technical authors have the following responsibilities:

- Observe official communication channels and spaces for documentation discussion.
- Provide timely responses to questions, requests for help, and suggestions, ideally
  within three working days.
- Transform questions and requests about documentation into well-defined work items.
- Review and triage member-submitted GitHub issues for fitness as tasks on Jira, GitHub,
  and for CODA.
- Break down and refine GitHub issues into easily-manageable pieces.
- Review volunteer applications to GitHub issues, ideally within three working days.
- Monitor pull requests on GitHub.
- Provide timely reviews of documentation pull requests that follow the contribution
  guidelines, ideally within ten working days.
- Assist documentation pull requests that have minor defects that block merging.
- Merge members' documentation pull requests when all required reviews are satisfied,
  ideally within three working days.
- Provide documentation mentorship to members.


Responsiveness metrics
----------------------

We employ metrics to measure how consistently we respond to community engagement. They
are incorporated into the team's processes and cadence, with a schedule that's
proportionate to the team's capacity. Metrics are tracked over six-month cycles by the
technical authors.

Responsiveness is tracked for issues and pull requests that are fit. Response time will
begin when all conditions for fitness are met.

.. list-table::
    :header-rows: 1
    :widths: 3 3 2

    * - Responsibility
      - Measure
      - Best effort
    * - Review and triage member-submitted issues on GitHub
      - Time to triage
      - 3 work days
    * - Add valuable tasks to CODA aggregator
      - Number of tasks added
      - 5
    * - Provide timely reviews of documentation pull requests that follow the
        contribution guidelines
      - Time from opening to first maintainer review
      - 3 work days for small

        10 work days for large
    * - Merge members' documentation pull requests when all required reviews are
        satisfied
      - Time from final approval to merge
      - 3 work days


Issue fitness
-------------

For timely triaging, a member-submitted documentation issue must meet certain conditions
of fitness:

- Be relevant to the project's goals
- Have an achievable scope
- Have no duplicates
- Fill each field of the project's issue template
- If the issue proposes new content, propose all new page names, Diátaxis categories,
  and locations
- If the issue requests documentation maintenance, chart the changes needed for each
  affected page


Issue assignment and funnelling
-------------------------------

Community-submitted documentation issues are tracked in either Jira or GitHub, depending
on who will work on it.

Once an issue is deemed fit, we use multiple criteria to decide assignment and where to
track the issue.

.. list-table::
    :header-rows: 1
    :widths: 1 3 2 1

    * - Issuer
      - Criteria
      - Assigned to
      - Goes to
    * - Community
      - The issue's gravity and urgency are high.
      - Starcraft member
      - Jira
    * - Community
      - The issue isn't grave or urgent.

        A contributor volunteers to work on the issue.

        The gravity and complexity of the issue is commensurate with the contributor's
        knowledge, ability, and reputation.
      - Community member
      - GitHub
    * - Anyone
      - The issue isn't grave or urgent.

        The issue would be a valuable achievement for a contributor.

        The issue has low-to-medium complexity.

        The issue has received no volunteers for a significant time since it was opened.
      - CODA aggregator
      - GitHub


Pull request fitness
--------------------

For a timely merge, a member's documentation pull request must meet certain conditions
of fitness:

-  Address an issue that was approved by a project maintainer
-  Follow the conventional commit messaging format
-  Add or update necessary documentation and tests


Documentation contribution protocols
------------------------------------

Here are our step-by-step protocols for facilitating the contribution experience.


Issue lifecycle
~~~~~~~~~~~~~~~

#. The community member creates an issue.

#. A maintainer reviews the issue for fitness and relevance.

#. The maintainer administrates the issue's tags.

#. As needed, the maintainer and the issuer discuss the problem and solution to
   accurately determine the scope and an achievable solution.

#. The maintainer funnels it into one of the three issue streams or closes it.

   #. **Jira ticket**. When the team is ready to start the ticket(s), they assign it to
      a team member, schedule it for a pulse, and give it story points. The assignee
      completes the work within the pulse.

   #. **GitHub issue**. At a later point, a contributor volunteers for the task. The
      contributor can be the same as the issuer. A TA or engineer provides advice and
      guidance to the contributor, at their discretion. The contributor completes the
      work, and opens a pull request for the changes.

   #. **CODA issue**. At a later point, a contributor volunteers for the task. A TA
      reaches out to the contributor, and provides hands-on help with planning and
      executing the task. The contributor completes the work, and opens a pull request
      for the changes.

   #. **Unfit issue**. The maintainer describes why the issue isn't fit in a comment,
      and closes it.

#. Once the pull request for the ticket is merged, the maintainer links the PR in the
   ticket. If they judge the issue resolved, they close the ticket. If not, they leave a
   comment about next steps.


Pull request lifecycle
~~~~~~~~~~~~~~~~~~~~~~

#. The contributor opens a PR.

#. The ``CODEOWNERS`` file automatically adds TAs as reviewers.

#. The PR is subjected to automated checks in CI workflows.

#. A maintainer adds an engineer as a second reviewer, usually
   themself.

#. The maintainer performs a basic check for new and updated tests (when applicable) and
   verifies the result of the CI test suite.

   #. If the PR is missing necessary changes to CI tests, they ask the contributor to
      add them.

   #. If the PR fails any required checks, they ask the contributor to fix the errors.

#. Once the PR is passing all required checks, the assigned reviewers
   review the PR. Reviews contain a combination of comments and
   suggestions.

   #. If the review is an approval, the PR is good to merge. Some
      suggestions might be posted as nice-to-haves. It's up to the contributor to decide
      whether to address them.

   #. If the review is a commentary, the PR might not yet be ready for merging. The
      comments and suggestions are recommendations.

   #. If the review requests changes, the PR is for certain not ready for merging.

#. The contributor addresses all comments and suggestions. If they disagree with a
   suggestion, they provide a reason.

#. The reviewers look at the solutions to their comments and suggestions, and either
   provide approval or follow-up reviews.

#. The review loops as many times until reviewers are satisfied by the completeness of
   the PR.

#. A maintainer merges the PR.
