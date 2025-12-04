.. meta::

    :description: Page meta descriptions are important for SEO of documentation for Starcraft projects. Learn how to add a meta description to a page.

.. _how-to-add-a-page-meta-description:

Add a page meta description
===========================

Search engines present *options*, and the user *chooses* from them. A search result is
composed of the page's title, snippet, and icon. From these elements, the user
decides what pages to visit.

A *meta description* is a short summary that the page provides to web systems. Search
engines often copy it word-for-word in the search result snippet. The meta description
helps the user decide in advance whether a page contains what they seek. It therefore
has a direct impact on whether the user visits our documentation.

**All new pages in a product documentation set must include a meta description.**


Write the meta description
--------------------------

Think of a meta description as a one-line summary that you would give to someone in a
hurry, like an elevator pitch.

It doesn't have to be clever or original. Often, you can reuse simple descriptions from
the page text itself.

Put the most important words or phrases early in the description. If the user sees that
the words they're thinking of are included in the title and description, they are more
likely to visit the page.

Every word counts in a meta description. Don't make it too short, or too long. An
average of 140 characters is good to aim for. You have a maximum of 160. Cut any detail
about the topic that isn't essential to helping the user make a decision.

Frame the meta description as either an action the user will perform, or a technical
description of a tool, process, or the page itself.

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

    Learn how to install Starcraft on a local system. Starcraft is available as a snap on all GNU/Linux systems that support systemd.
