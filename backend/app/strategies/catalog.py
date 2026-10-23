from app.schemas.chat import PipelineInfo


PIPELINES: list[PipelineInfo] = [
    PipelineInfo(id="simple", name="Simple RAG", status="implemented", description="Dense retrieval plus cited generation."),
    PipelineInfo(id="two_step", name="Two-step RAG", status="implemented", description="Retrieve, select context, then generate."),
    PipelineInfo(id="hybrid", name="Hybrid RAG", status="implemented", description="Dense plus BM25-style lexical retrieval fusion."),
    PipelineInfo(id="reranked", name="Reranked RAG", status="experimental", description="Local score-based reranking over hybrid candidates."),
    PipelineInfo(id="corrective", name="Corrective RAG", status="implemented", description="Bounded rewrite fallback when evidence is weak.", uses_langgraph=True),
    PipelineInfo(id="multi_query", name="Multi-query", status="experimental", description="Runs simple local query variants and fuses evidence."),
    PipelineInfo(id="query_decomposition", name="Query Decomposition", status="experimental", description="Splits compound questions into smaller retrieval probes."),
    PipelineInfo(id="parent", name="Parent-document", status="experimental", description="Returns neighboring chunks from the same document."),
    PipelineInfo(id="compression", name="Contextual Compression", status="experimental", description="Selects compact evidence snippets before generation."),
    PipelineInfo(id="sentence_window", name="Sentence Window", status="experimental", description="Expands matching chunks with nearby sentence context."),
    PipelineInfo(id="hyde", name="HyDE-inspired", status="experimental", description="Uses a generated local hypothetical answer as retrieval text."),
    PipelineInfo(id="contextual", name="Contextual Retrieval", status="experimental", description="Adds section and filename context to retrieval."),
    PipelineInfo(id="self_rag", name="Self-RAG-inspired", status="planned", description="Planned prompted reflection, not original trained Self-RAG."),
    PipelineInfo(id="adaptive", name="Adaptive RAG", status="experimental", description="Routes to simple, hybrid, or corrective by query shape.", uses_langgraph=True),
    PipelineInfo(id="iterative", name="Iterative RAG", status="planned", description="Planned bounded iterative retrieval and revision."),
    PipelineInfo(id="multihop", name="Multi-hop RAG", status="planned", description="Planned subquestion evidence chaining."),
    PipelineInfo(id="structured", name="Structured-data RAG", status="planned", description="Planned read-only structured data retrieval."),
    PipelineInfo(id="temporal", name="Temporal RAG", status="planned", description="Planned time-aware filtering and ordering."),
    PipelineInfo(id="federated", name="Federated Retrieval", status="experimental", description="Local docs plus optional X retrieval status."),
    PipelineInfo(id="graph", name="GraphRAG", status="planned", description="Requires graph extraction and graph storage."),
    PipelineInfo(id="raptor", name="RAPTOR-style", status="planned", description="Requires hierarchical summaries."),
    PipelineInfo(id="multimodal", name="Multimodal RAG", status="planned", description="Requires OCR or vision embedding configuration."),
    PipelineInfo(id="agentic", name="Agentic RAG", status="planned", description="Requires tool allowlists and stronger safety controls.", uses_langgraph=True),
    PipelineInfo(id="multi_agent", name="Multi-Agent RAG", status="planned", description="Requires benchmark justification for added cost."),
    PipelineInfo(id="flare", name="FLARE-inspired", status="planned", description="Planned active retrieval during generation."),
    PipelineInfo(id="replug", name="REPLUG-inspired", status="planned", description="Planned retrieval-conditioned scoring experiments."),
    PipelineInfo(id="late_chunking", name="Late Chunking", status="planned", description="Requires long-context embedding support."),
]

