# Something in the Trees RAG

This will be a Retrieval Augmented Generation system that can be used by LLMs to enrich their models about cryptids and cryptid lore.  

This project should use a multi-agent design to build the project.  Voyage AI will be the embeddings system.  ChromaDB as a vector database. MCP will be a composable layer that we can add-on.

Our dataset will come from Wikipedia at https://en.wikipedia.org/wiki/List_of_cryptids. We need to develop a script for retrieval and updates.  

Summary on requirements
- Voyage AI embeddings model (cheapest plans)
- ChromaDB
- Wikipedia dataset (https://en.wikipedia.org/wiki/List_of_cryptids)
- RAG as a composable layer
