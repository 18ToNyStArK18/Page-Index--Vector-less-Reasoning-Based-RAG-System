from __future__ import annotations
from typing import List , Dict , Any
from models import TreeNode
import fitz
from rich.tree import Tree as RichTree
from rich import print as rich_print

#TODO: Build the actual toc from the document
#for this if the metadata has the toc we can get the toc directly using the pymupdf library else
# we can send the first 20 pages of the document to an llm to generate the toc 
#TODO: need to extract the pdf content and pass it accordingly
#TODO: need to pass it to the llm for proper summary

class TreeBuilder:
    def __init__(self , max_pages_per_node :int = 10):
        self.max_pages_per_node = 10
        self.nodes = 1
    
    def buildLeafNodes(self,title: str , page_start: int , page_end: int)-> List[TreeNode]:
        """
            this takes the content in the section and if the content is large it splits into chuncks
        """
        chunks = []
        i = page_start
        idx = 1
        while i <= page_end:
            chunkend = min(page_end , i + self.max_pages_per_node)
            
            chunk_title = f"{title}_{idx}"
            # this is the mock just random data
            chunks.append(TreeNode(
                node_id=f"leaf_{self.nodes}",
                title=chunk_title,
                summary=f"Content for {chunk_title} ({i}-{chunkend})",
                page_start=i,
                page_end=chunkend,
            ))     
            self.nodes += 1 
            idx = idx + 1      
            i += self.max_pages_per_node
        return chunks
    
    def process_toc_nodes(self, toc_items) -> TreeNode:
        title = toc_items["title"]
        page_start = toc_items["page_start"]
        page_end = toc_items["page_end"]
        subsections = toc_items.get("sections", [])
        #create a temp node for this section
        currentNode = TreeNode(
            node_id=f"node_{self.nodes}",title=title,page_start=page_start,page_end=page_end , summary=None
        )
        self.nodes += 1
        
        if subsections:
            # recurssively call this
            for sub in subsections:
                child = self.process_toc_nodes(sub)
                currentNode.children.append(child)
        # normal base case
        else:
            chunks = self.buildLeafNodes(title=title,page_start=page_start,page_end=page_end)
            
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
    
    def extract_nested_toc_from_pdf(self,pdf_path: str) -> List[Dict[str, Any]]:
        """ this function extracts the toc from the documment and then returns the toc skeleton"""
        doc = fitz.open(pdf_path)
        total_pages = doc.page_count
        raw_toc = doc.get_toc()

        if not raw_toc:
            """need to call the fucntion which sends the first 20 pages to llm to generate the toc"""
        normalized_toc = []
        for i in range(len(raw_toc)):
            level , title , page = raw_toc[i]
            end_page = total_pages
            for j in range(i+1,len(raw_toc)):
                next_lvl, _, next_start = raw_toc[j]
                if(next_lvl <= level):
                    end_page = max(page,next_start)
                    break
            normalized_toc.append({
            "level": level,
            "title": title,
            "page_start": page,
            "page_end": end_page,
            "sections": []
            })
        # print(normalized_toc[:10])
        
        nested_toc = []
        stack = []
        
        for item in normalized_toc:
            curr_lvl = item.pop("level")
            
            while stack and stack[-1][0] >= curr_lvl:
                stack.pop()
            
            if not stack:
                nested_toc.append(item)
            else:
                parent = stack[-1][1]
                parent["sections"].append(item)
            
            stack.append((curr_lvl,item))
            
        return nested_toc

    def visualize_with_rich(self,custom_node, rich_tree_root=None):
        """Recursively converts custom TreeNode to a Rich Tree representation."""
        label = f"[bold yellow]{custom_node.node_id}[/bold yellow]: [cyan]{custom_node.title}[/cyan] (Pages {custom_node.page_start}-{custom_node.page_end})"
        
        if rich_tree_root is None:
            rich_tree_root = RichTree(label)
        else:
            rich_tree_root = rich_tree_root.add(label)
            
        for child in custom_node.children:
            self.visualize_with_rich(child, rich_tree_root)
            
        return rich_tree_root


tree = TreeBuilder()
nested_toc = tree.extract_nested_toc_from_pdf(pdf_path = "/home/vedavyas/forfun/RAG/TheoryOfComputation.pdf")

chapter_nodes = tree.compile_tree(nested_toc)

for node in chapter_nodes:
    rich_print(tree.visualize_with_rich(node))