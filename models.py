from __future__ import annotations
from dataclasses import dataclass , field
from typing import List
@dataclass
class TreeNode:
    nodeid : str
    title : str
    summary : str
    start : int
    end : int
    children : List[TreeNode] = field(default_factory=list)
    

leafNode = TreeNode(
    nodeid="section1_1",title="Idk what to put",summary="normally llm generated summary place holder for now" , start=10,end=20
)

chapterNode = TreeNode(
    nodeid="RootNode",title="IDK",summary="LLM generated summary",start=1,end=10
)
print(chapterNode)
chapterNode.children.append(leafNode)
print(chapterNode)