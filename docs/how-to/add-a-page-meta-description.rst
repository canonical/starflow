.. meta::

    :description: Page meta descriptions are important for SEO of documentation for Starcraft projects. Learn how to add a meta description to a page.

.. _how-to-add-a-page-meta-description:

Add a page meta description
===========================

A *meta description* provides a machine-readable summary of a web page. Search engines
often copy this description word-for-word in search results. Since snippets are one way
users decide which page to visit, the meta description has a direct effect on whether
our documentation is read.

A well-written meta description has a better chance of being used by a search engine as
the page's snippet.

**All new pages in a product documentation set must include page metadata.**


Write the meta description
--------------------------

Think of a meta description as a one-line summary that you would pass to someone in a
hurry. It's like an elevator pitch for your page.

The description doesn't have to be clever or original. Often, you can reuse simple
descriptions from the page text itself.

Every word counts in a meta description. Don't make it too short, or too long. An
average of 120 characters is good to aim for. You have a maximum of 160. Cut any detail
about the topic that isn't essential to helping the user make a decision.

Think of how you're framing the meta description. It should be written as an action the
user will perform, or a technical description of a tool, process, or the page itself.

.. list-table::

    * - Mode
      - Starts with phrases like...
    * - Action
      - Get started with

        Learn about

        Find info on
    * - Description
      - The encabulator is a feature that

        Starcraft is a suite of tools

        The list of supported platforms in Starcraft

Don't use pronouns such as *I* or *we*. These stand out and will distract the reader
from making a choice.


Add the description
-------------------

At the top of the page, add:

.. code-block:: rst

    .. meta::

        :description: <description>

The meta description must be one line, because Sphinx options don't support line breaks.


Example
-------

This is an example of a good meta description for *Set up Starcraft*.

    Learn how to install Starcraft on a local system. Starcraft is available as a snap on all GNU/Linux systems that supports systemd.
