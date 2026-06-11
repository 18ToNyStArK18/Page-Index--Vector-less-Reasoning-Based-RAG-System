from __future__ import annotations
from models import TreeNode
from google.genai import types

class QueryHandler:
    def __init__(self,client,model,model2):
        self.client = client
        self.model = model
        self.model2 = model2
        
    async def get_nodes(self , query : str , rootNode: TreeNode):
        """This is the retrieval phase where the we pass the question and the tree to llm"""
        
        tree_search_prompt = f"""
        Given the document tree and query, return the node IDs to retrieve.
        return the node IDs of the leaf node only and give the most relavent node first 
        Tree: {rootNode} 
        Query: {query}
        Return JSON only: {{"node_ids": ["node_1", "node_2"]}}
        """
        print(f" [GEMINI API] Calling {self.model} to get the required nodes for the query {query} ")
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model,
                contents=tree_search_prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    response_mime_type="application/json",
                )
            )
            
            result = response.text
            
        except Exception as e:
            print(f"   [ERROR] Failed on '{query}': {e}")
            result = '{"node_ids": []}'
        print(result)
        print("-"*100)
        return result
   
    def find_node_by_id(self,current_node: TreeNode, target_id: str) -> TreeNode:
        if current_node.node_id == target_id:
            return current_node
        for child in current_node.children:
            found = self.find_node_by_id(child, target_id)
            if found:
                return found
        return None  
    
    async def generate_final_answer(self,query: str, retrieved_ids: list[str], root_node: TreeNode, pdf_extractor) -> str:
        context_text = ""
        for n_id in retrieved_ids:
            node = self.find_node_by_id(root_node, n_id)
            if node:
                raw_text = pdf_extractor(node.page_start, node.page_end)
                context_text += f"\n--- Section: {node.title} (Pages {node.page_start}-{node.page_end}) ---\n{raw_text}\n"

        synthesis_prompt = f"""
        You are an expert Computer Science tutor helping a student.
        Answer the user's question using ONLY the provided textbook context below.
        If the answer is not contained in the context, explicitly state that the textbook does not cover it.
        
        Question: {query}
        
        Textbook Context:
        {context_text}
        """
        print("\n[api] generating final answer...")
        try:
            response = await self.client.aio.models.generate_content(
                model=self.model2,
                contents=synthesis_prompt,
                config=types.GenerateContentConfig(temperature=0.3)
            )
            return response.text
        except Exception as e:
            return f"[ERROR] generation failed: {e}" 
    