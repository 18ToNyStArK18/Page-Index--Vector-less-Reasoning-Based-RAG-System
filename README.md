# PageIndex Vector-less RAG System
LLMs have become powerfull enough to understand a document and answer the questions. However, they are constrained by the **context window**. Even though the latest LLMs have high context window research has shown that model performances **reduces** as the context window increases (https://www.trychroma.com/research/context-rot).

To tackle this situation we use **Retrieval Augmented Generation(RAG)**. Instead of passing the entire document we only pass the **relavent chuncks** of data based on the user query which significantly **reduces the tokens** in the prompt and thus **reduces** the context window.

### Majority of the RAG systems do the following:
    

    1. Divide the PDF into chunks of fixed size
    2. Vectorize the chunks and store them in a vector database
    3. Process the user query
    4. Select the top-*k* relevant chunks

### Disadvantages of this general apprach
This relies on the semantic embeddings and vector database to indentify the relavent chuncks.
1. **Query and knowledge space mismatch.** Vector retrieval assumes that the most semantically similar text to the query is also the most relevant. But this isn’t always true: queries often express intent, not content.
2. **Hard chunking breaks semantic and contextual integrity.** Documents are split into fixed-size chunks for embedding. This “hard chunking” often cuts through sentences, paragraphs, or sections, fragmenting meaning and context.

Because of these limitaions even advanced systems like claude code moved away from the Vector-RAGs (https://rlancemartin.github.io/2025/04/03/vibe-code/)

## PageIndex
The core idea behind this project is this mimics how a human finds the relavent chuncks from a long document.
### The advantages


**Natural Chuncking**

Rather than arbitrarily chuncking the data we chunck based on semantically coherent sections (e.g., sections , subsections or chapters). This preserves the logical continuity and prevent hallucinations.

**Semantic Similarity ≠ True Relevance**

Reasoning-based retrieval focusses on the contextual relavence not just the similarity. The model reads the Table of Contents Tree, interprets the query’s intent, and navigates to sections that actually contain the answer. This is exactly how a human navigate.
## Implementaion
**Tree Model:**
```python
class TreeNode:
    node_id: str
    title: str
    summary: str
    page_start: int
    page_end: int
    children: List["TreeNode"] = field(default_factory=list)
```
**Example:**

```json
...
{
  "node_id": "node_35",
  "title": "Deterministic finite automata",
  "page_start": 31,
  "page_end": 39,
  "summary": "This chapter introduces deterministic finite automata...",
  "children": [
    {
      "node_id": "node_36",
      "title": "A first example of a finite automaton",
      "page_start": 34,
      "page_end": 36,
      "summary": "Finite Automata Routing Summary...",
      "children": []
    },
    {
      "node_id": "node_38",
      "title": "A second example of a finite automaton",
      "page_start": 36,
      "page_end": 37,
      "summary": "A finite automaton accepting language A...",
      "children": []
    }
  ]
}
...
```
    
### Pipeline
1. **Build the TOC Tree**

   * Extract the Table of Contents (TOC) from the PDF.
   * Construct a hierarchical tree where each node represents a chapter, section, or subsection.

2. **Generate Hierarchical Summaries**

   * Extract the content corresponding to each node.
   * Generate summaries recursively from leaf nodes up to the root, allowing each node to capture the essence of its subtree.

3. **Cache the Tree**

   * Store the TOC tree, node metadata, and generated summaries in MongoDB.
   * This preprocessing step is performed once per document and reused across queries.

4. **Query-Time Retrieval**

   * When a user submits a query, the query and the summarized TOC tree are provided to the LLM.
   * The LLM reasons over the document structure and identifies the most relevant nodes.

5. **Content Extraction**

   * Retrieve the full text associated with the selected nodes.

6. **Answer Generation**

   * Pass the user query and the extracted text to the LLM.
   * Generate a grounded answer using only the relevant portions of the document.

## Prerequisites
Before you begin, ensure you have the following installed on your machine:
1. **Python 3.10+**
2. **MongoDB Community Server:** The core database for caching the vector-less trees. 
3. **MongoDB Shell (`mongosh`):** Required for interacting with the database via the terminal.
4. **Ollama:** Install ollama and pull the "llama3.2:3b" model this is used to create summaries for the nodes
## Installation
1. **Clone the repo**
   ```bash
   git clone https://github.com/18ToNyStArK18/Page-Index--Vector-less-Reasoning-Based-RAG-System.git
   cd Page-Index--Vector-less-Reasoning-Based-RAG-System
   ```
2. **Install the dependencies**

   ```bash
   pip install -r requirements.txt
   ```
3. **Set your environment variable**

   ```bash
   export GEMINI_API_KEY="your_api_key_here"
   ```
4. **Change the pdf file path(optional)**

      If you want to use diffrenent file change the pdf_path variable in the main function and if you want to change the models of gemini change the variables in the main function in the same file

      **model1**: Relavent node extraction

     **model2**: Generating the answer for the query
5. **Run the pagenindex.py**
   ```bash
   python pageindex.py
   ```
## Evaluation Benchmarks
This system was thoroughly evaluated against a "Hard Mode" verification dataset consisting of highly complex, conceptually overlapping questions from the Introduction to Theory of Computation textbook

 **Retrieval Hit Rate**: 9 / 9 (**100%** Accuracy)

**Lexical Trap Resilience:** Successfully isolated identical vocabulary terms across entirely different domains (e.g., distinguishing between a Pushdown Automaton definition in Chapter 3 and a CFG-to-PDA structural transformation proof in Chapter 4).

**Deep Proof Resolution:** Extracted precise variable criteria from deep within complex contradictions (e.g., isolating specific strings like s=apbpcp used for the context-free pumping lemma).
## References

1. Mingtian Zhang, Yu Tang, and PageIndex Team. *PageIndex: Next-Generation Vectorless, Reasoning-based RAG*. PageIndex Blog, September 2025.
