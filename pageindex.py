from __future__ import annotations
from typing import List , Dict , Any
from models import TreeNode
import fitz
from rich.tree import Tree as RichTree
from rich import print as rich_print
import asyncio
import aiohttp
from dbmanager import TreeDB
#TODO: fall back for the toc if the meta data doesnt have a toc then send it to the lmm to create a toc
#TODO: write the toc into some db so that we dont need to create a toc for the same pdf multiple times


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
    
    def __init__(self , max_pages_per_node :int = 10 , max_concurrent_calls: int = 1):
        self.max_pages_per_node = max_pages_per_node
        self.nodes = 1
        self.semaphore = asyncio.Semaphore(max_concurrent_calls)
        self.local_model = "llama3.2:1b"
        self.ollama_url = "http://localhost:11434/api/generate"
     
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
    
    async def call_llm_leaf_summary(self, title: str, raw_text: str) -> str:
        async with self.semaphore:
            prompt = f"""
            You are a technical document routing agent.
            Write a dense, 5-sentence routing summary of this section: '{title}'. 
            Capture the core concepts and keywords to help a search engine find this page later.
            
            Text Content:
            {raw_text} 
            """
            print(f"   [Local API] Calling {self.local_model} for leaf: {title}...")
            
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(self.ollama_url, json={
                        "model": self.local_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.2,
                        }
                    }) as response:
                        result_data = await response.json()
                        result = result_data['response'].strip()
            except Exception as e:
                print(f"   [ERROR] Failed on {title}: {e}")
                result = f"Summary unavailable for {title} due to local API error."
            print(result)
            print("-"*100)
            return result
    
    async def call_llm_branch_summary(self, title: str, child_summaries: List[str]) -> str:
        async with self.semaphore:
            combined_children = "\n".join([f"- {s}" for s in child_summaries])
            prompt = f"""
            You are a technical document routing agent.
            Synthesize these sub-section summaries into a single, cohesive 5-sentence 
            overarching summary for the parent chapter: '{title}'.
            
            Sub-sections:
            {combined_children}
            """
            print(f" [Local API] Calling {self.local_model} for branch roll-up: {title}...")
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(self.ollama_url, json={
                        "model": self.local_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.2}
                    }) as response:
                        result_data = await response.json()
                        result = result_data['response'].strip()
            except Exception as e:
                print(f" [ERROR] Failed on branch {title}: {e}")
                result = f"Branch summary unavailable for {title}."
            print(result)
            print("-"*100)
            return result

    async def populate_tree_summaries_dfs(self,node:TreeNode,pdf):
        """
            This is the way i am implementing the summarise
            First get the summaries of the leaf nodes by sending the raw text to llm
            For the branch node send the summaries of all the children and get a unified summary for the branch node    
        """
        if node.children:
            tasks = [self.populate_tree_summaries_dfs(child, pdf) for child in node.children]
            await asyncio.gather(*tasks)
        
        if not node.children:
            # this is a leaf node (base case)
            raw_text = pdf(node.page_start,node.page_end)
            node.summary = await self.call_llm_leaf_summary(node.title,raw_text)
        else:
            #send the summaries of the children
            child_summaries = [child.summary for child in node.children]
            node.summary = await self.call_llm_branch_summary(node.title,child_summaries)

def to_dict(node : TreeNode):
    return {
        "node_id": node.node_id,
        "title": node.title,
        "page_start": node.page_start,
        "page_end": node.page_end,
        "summary": node.summary,
        "children": [to_dict(child) for child in node.children]
    }
    
def dict_to_tree(tree_dict: Dict[str, Any]) -> TreeNode:
    """
    Recursively converts a nested dictionary back into a full TreeNode hierarchy.
    """
    node = TreeNode(
        node_id=tree_dict["node_id"],
        title=tree_dict["title"],
        page_start=tree_dict["page_start"],
        page_end=tree_dict["page_end"],
        summary=tree_dict.get("summary")
    )
    
    if "children" in tree_dict:
        node.children = [dict_to_tree(child_dict) for child_dict in tree_dict["children"]]
        
    return node
 
def visualize_with_rich(custom_node, rich_tree_root=None):
        """Recursively converts custom TreeNode to a Rich Tree representation."""
        label = f"[bold yellow]{custom_node.node_id}[/bold yellow]: [cyan]{custom_node.title}[/cyan] (Pages {custom_node.page_start}-{custom_node.page_end})\n (summary: {custom_node.summary})"
        
        if rich_tree_root is None:
            rich_tree_root = RichTree(label)
        else:
            rich_tree_root = rich_tree_root.add(label)
            
        for child in custom_node.children:
            visualize_with_rich(child, rich_tree_root)
            
        return rich_tree_root

async def main(): 
    ## create a tree
    tree = TreeBuilder()
    pdf_path = "/home/vedavyas/forfun/RAG/TheoryOfComputation.pdf"

    ##get the toc
    nested_toc = tree.extract_nested_toc_from_pdf(pdf_path)
    pdf = create_pdf_text_extractor(pdf_path)

    ## create the tree with the help of the toc we extracted 
    chapter_nodes = tree.compile_tree(nested_toc)

    ## dummy root node
    rootNode = TreeNode("root","root","na",0,0)
    for node in chapter_nodes:
        rootNode.children.append(node)

    ## populate all the children
    for node in rootNode.children:
        await tree.populate_tree_summaries_dfs(node,pdf)
        
        
        
    ## to save it in the database
    tree_dict = to_dict(rootNode)
    dbManager = TreeDB()
    dbManager.save_tree(pdf_path,tree_dict)



if __name__ == "__main__":
    asyncio.run(main())