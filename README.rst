About
-----

This is a wrapper for Tornado:

* Collect and mount URLs
* Environments
* Pre-configured Postgres and Cassandra support

Many time I start writing something in Tornado, it's not simple to make these fundamental thing.
As a newbie to Python, I made these while I was learning how it work.

These projects are currently lack of documents and good practise. Contributions are very welcomed!

Usage
-----

Get started by creating a skeleton project::

    $ python3 -m tokit

Inside src/ folder, put your modules.
Each modules should contains templates, Python source, frontend as a completed functional unit ...

If a module interact with other modules, use `tokit.Event` for hooking.
