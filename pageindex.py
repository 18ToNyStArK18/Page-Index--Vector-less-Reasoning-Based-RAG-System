from __future__ import annotations
from typing import List , Dict , Any
from models import TreeNode

#TODO: Build the actual toc from the document
#for this if the metadata has the toc we can get the toc directly using the pymupdf library else
# we can send the first 20 pages of the document to an llm to generate the toc 
#TODO: need to extract the pdf content and pass it accordingly
#TODO: need to pass it to the llm for proper summary

class TreeBuilder:
    def __init__(self , max_pages_per_node :int = 10):
        self.max_pages_per_node = 10
        self.nodes = 1
    
    def buildLeafNodes(self,title: str , start: int , end: int)-> List[TreeNode]:
        """
            this takes the content in the section and if the content is large it splits into chuncks
        """
        chunks = []
        i = start
        idx = 1
        while i <= end:
            chunkend = min(end , i + self.max_pages_per_node)
            
            chunk_title = f"{title}_{idx}"
            # this is the mock just random data
            chunks.append(TreeNode(
                node_id=f"leaf_{self.nodes}",
                title=chunk_title,
                summary=f"Content for {chunk_title} ({i}-{chunkend})",
                start=i,
                end=chunkend,
            ))     
            self.nodes += 1 
            idx = idx + 1      
            i += self.max_pages_per_node
        return chunks
    
    def process_toc_nodes(self, toc_items) -> TreeNode:
        title = toc_items["title"]
        start = toc_items["page_start"]
        end = toc_items["page_end"]
        subsections = toc_items.get("sections", [])
        #create a temp node for this section
        currentNode = TreeNode(
            node_id=f"node_{self.nodes}",title=title,start=start,end=end , summary=None
        )
        self.nodes += 1
        
        if subsections:
            # recurssively call this
            for sub in subsections:
                child = self.process_toc_nodes(sub)
                currentNode.children.append(child)
        # normal base case
        else:
            chunks = self.buildLeafNodes(title=title,start=start,end=end)
            
            if len(chunks) == 1:
                currentNode.summary =  chunks[0].summary
            else:
                currentNode.children = chunks        
        return currentNode
    
    def compile_tree(self, toc_skeleton: List[Dict[str, Any]]) -> List[TreeNode]:
        """for all chapters"""
        chapter_nodes = []
        for item in toc_skeleton:
            chapter_nodes.append(self.process_toc_nodes(item))
        return chapter_nodes
    
## mock data
multi_level_toc = [
    {
        "title": "Chapter 1: Process Management",
        "page_start": 1,
        "page_end": 25,
        "sections": [
            {
                "title": "Section 1.1: Threads",
                "page_start": 1,
                "page_end": 8
            },
            {
                "title": "Section 1.2: CPU Scheduling",
                "page_start": 9,
                "page_end": 25 
            }
        ]
    }
]

tree = TreeBuilder()
nodes = []
nodes = tree.compile_tree(toc_skeleton=multi_level_toc)

for node in nodes:
    print(node)
    for child in node.children:
        print(f"  -> {child}")
        for subchild in child.children:
            print(f"      -> {subchild}")