from __future__ import annotations
from dataclasses import dataclass , field
from typing import List
@dataclass
class TreeNode:
    node_id : str
    title : str
    summary : str
    page_start : int
    page_end : int
    children : List[TreeNode] = field(default_factory=list)
