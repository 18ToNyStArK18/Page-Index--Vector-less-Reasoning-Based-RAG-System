from __future__ import annotations
from typing import List , Dict , Any
from models import TreeNode
import fitz
from rich.tree import Tree as RichTree
from rich import print as rich_print
#TODO: fall back for the toc if the meta data doesnt have a toc then send it to the lmm to create a toc
#TODO: need to extract the pdf content and pass it accordingly
#TODO: need to pass it to the llm for proper summary




def create_pdf_text_extractor(pdf_path: str):
    """
    Opens the PDF once and returns a highly efficient extraction function.
    """
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    
    def extract_text(page_start: int, page_end: int) -> str:
        extracted_text = []
        
        start_idx = max(0, page_start - 1)
        end_idx = min(total_pages - 1, page_end - 1)
        
        for i in range(start_idx, end_idx + 1):
            page = doc.load_page(i)
            extracted_text.append(page.get_text("text"))
            
        raw_string = "\n".join(extracted_text)
        
        clean_string = " ".join(raw_string.split())
        return clean_string
        
    return extract_text
class TreeBuilder:
    def __init__(self , max_pages_per_node :int = 10):
        self.max_pages_per_node = max_pages_per_node
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
        label = f"[bold yellow]{custom_node.node_id}[/bold yellow]: [cyan]{custom_node.title}[/cyan] (Pages {custom_node.page_start}-{custom_node.page_end})\n (summary: {custom_node.summary})"
        
        if rich_tree_root is None:
            rich_tree_root = RichTree(label)
        else:
            rich_tree_root = rich_tree_root.add(label)
            
        for child in custom_node.children:
            self.visualize_with_rich(child, rich_tree_root)
            
        return rich_tree_root
    def call_llm_leaf_summary(self,title: str, raw_text: str) -> str:
        """Mock API Call: Summarizes raw textbook text."""
        prompt = f"Write a dense, 2-sentence routing summary of this section: '{title}'. Text: {raw_text[:1000]}..."
        return f"Detailed summary of raw text for {title}."

    def call_llm_branch_summary(self,title: str, child_summaries: list[str]) -> str:
        """Mock API Call: Synthesizes a parent summary from child summaries."""
        combined_children = "\n".join([f"- {s}" for s in child_summaries])
        prompt = f"Synthesize these sub-section summaries into a single overarching summary for the chapter: '{title}'. Sub-sections:\n{combined_children}"
        return f"High-level rolled-up summary covering {len(child_summaries)} sub-sections."
    
    def populate_tree_summaries_dfs(self,node:TreeNode,pdf):
        """
            This is the way i am implementing the summarise
            First get the summaries of the leaf nodes by sending the raw text to llm
            For the branch node send the summaries of all the children and get a unified summary for the branch node    
        """
        for child in node.children:
            self.populate_tree_summaries_dfs(child,pdf)
        
        if not node.children:
            # this is a leaf node (base case)
            raw_text = pdf(node.page_start,node.page_end)
            node.summary = self.call_llm_leaf_summary(node.title,raw_text)
        else:
            #send the summaries of the children
            child_summaries = [child.summary for child in node.children]
            node.summary = self.call_llm_branch_summary(node.title,child_summaries)

tree = TreeBuilder()
nested_toc = tree.extract_nested_toc_from_pdf(pdf_path = "/home/vedavyas/forfun/RAG/TheoryOfComputation.pdf")
pdf = create_pdf_text_extractor("/home/vedavyas/forfun/RAG/TheoryOfComputation.pdf")
chapter_nodes = tree.compile_tree(nested_toc)
for node in chapter_nodes:
    tree.populate_tree_summaries_dfs(node,pdf)
for node in chapter_nodes:
    rich_print(tree.visualize_with_rich(node))