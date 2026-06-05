from __future__ import annotations
from typing import List , Dict , Any
from models import TreeNode
import fitz
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
            
        # for item in nested_toc:
        #     print(item)
        #     print("-"*100)

        return nested_toc
            
            
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
nested_toc = tree.extract_nested_toc_from_pdf(pdf_path = "/home/vedavyas/forfun/RAG/TheoryOfComputation.pdf")

chapter_nodes = tree.compile_tree(nested_toc)

for node in chapter_nodes:
    print(node)
    print("-"*100)