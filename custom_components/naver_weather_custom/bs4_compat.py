"""Compatibility boundary for Beautiful Soup's public Tag export."""

import bs4
from bs4 import BeautifulSoup
from bs4.element import Tag

if not hasattr(bs4, "Tag"):
    bs4.Tag = Tag


__all__ = ["BeautifulSoup"]
