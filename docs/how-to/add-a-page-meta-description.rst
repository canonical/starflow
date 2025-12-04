.. meta::

    :description: Page meta descriptions are important for SEO of documentation for Starcraft projects. Learn how to add a meta description to a page.

.. _how-to-add-a-page-meta-description:

Add a page meta description
===========================

Search engines present options for the user to consider. Each search result contains at
minimum the page's title, snippet, and icon. From these elements, the user chooses what
pages to visit.

A *meta description* is a short summary that search engines often reuse for the search
result's snippet. Since the meta description helps the user decide in advance whether a
page contains what they seek, it has a direct impact on whether the user visits our
documentation. Therefore, **all new pages in a product documentation set must include a
meta description.**


Write a meta description
------------------------

**Do** write the meta description *after* the page is written. The meta description is a
reflection of what's actually in the page.

**Do** reuse text from the page itself. The meta description doesn't have to be clever
or original.

**Do** share patterns between pages that share topics. Write as if page will be the only
search result from the documentation set. For example, use the same meta description for
every page of release notes, but with different version numbers.

**Do** frame sentences in terms of *actions* and *facts*.

.. list-table::
    :header-rows: 1

    * - Type
      - Starts with phrases like...
    * - Action
      - Get started with

        Learn about

        Find info on
    * - Fact
      - The encabulator is a module that

        The Chef init profile sets up a basic project file for

        Starcraft runs on architectures like AMD64, armhf, s390x

**Do** put key terms near the start.

**Do** aim for an average of 140 characters. Cut any detail about the topic that isn't
essential to helping the user make a decision.

**Don't** write to market, motivate, or compel. Marketing prose with rhetoric like the
following aren't appropriate for documentation.

    Don't just write code; deliver a product. Start your journey today and turn your
    project into a production-ready snap.

**Don't** include key terms that aren't in the page text.

**Don't** use pronouns such as *you*, *your*, *we*, or *our*. These waste space and
don't match the tone of a description.

**Don't** include grandiose qualities like *simple*, *easy*, or *best-in-class*.

**Don't** exceed 160 characters. Search engines will cut the snippet short.


Add a meta description
----------------------

At the top of the page, add:

.. code-block:: rst

    .. meta::

        :description: <description>

The meta description must be one line, because Sphinx options don't support line breaks.


Example
-------

This is an example of a good meta description for *Set up Starcraft*.

    Learn how to install Starcraft on a local system. Starcraft is available as a snap on all GNU/Linux systems that support systemd.
