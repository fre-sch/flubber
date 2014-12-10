flubber
=======

GUI for querying elasticsearch

Requires PyQt4, which is a pain to install with virtualenv/pip. Just use your
OS' distributor packages, or homebrew on OS X. If you're on Windows... you're
on your own.


2014-12-10
----------
Basic structure for elasticsearch querys implemented. This means, that the
query from the editor will always be wrapped as:

    {
        "query": <query from editor>,
        "sort": <sort from headers>,
        "size": <hardcoded to 100>
    }

Basic sorting of results implemented: clicking headers changes sort field and
direction. However, this is not really working as expected.

Treeview/model expect items to always have a fixed set of fields, but search
results have dynamic fields in undefined order. Need to redo the way
headers/columns work.
