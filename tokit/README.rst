About
-----

This is a wrapper for Tornado:

* Collect and mount URLs
* Environments
* Pre-configured Postgres and Cassandra support
* Production level setting: kill if blocked
* With a brother: https://github.com/manhgd/tofab deployment tool, systemd integration, operations (backup, sync, ...)


Many time I start writing something in Tornado, it's not simple to make these fundamental thing. As a newbie to Python, I made these while I was learning how it work.

These projects are currently lack of documents and good practise. Contributions are very welcomed!

Usage
-----

Get started by creating a skeleton project::

    $ python3 -m tokit

Inside src/ folder, put your modules.
Each modules should contains templates, JS, CSS, Python, ...

If a module interact with other modules, use tokit.Event for hooking.

Changelog
---------
* 0.4.2 Support Coffeescript / SASS
* 0.4.1 REST interface
* 0.4.1 Cassandra support
* 0.3   Skeleton tool
* 0.2   Postgres support
* 0.1   Initial functions
