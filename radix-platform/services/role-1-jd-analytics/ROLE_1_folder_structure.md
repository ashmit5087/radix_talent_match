
Folder structure

```
radix-jd-analytics/
  app/
    main.py                     FastAPI app, Swagger metadata
    config.py                   Settings from environment / .env (validated)
    schemas.py                  Shared RADIX schema + API models
    errors.py                   Error format, handlers, Swagger error examples
    api/routes.py               All endpoints
    services/
      document_parser.py        Validate and extract text (PDF/DOCX)
      llm_client.py             Gemini integration + typed errors (swap providers here)
      jd_analyzer.py            Prompt, retries, validation, grounding
      analysis_store.py         Saved analyses (SQLite, default): jd_id, company, role, skills
      supabase_store.py         Same interface, stored in Supabase (optional)
      embedding_service.py      Local Sentence Transformers embeddings (lazy loaded)
      vector_store.py           ChromaDB: chunking, index, search, list, delete, clear
  data/chroma/                  Local index (generated, git-ignored)
  docs/api-contract.md          Endpoint reference with examples
  contracts/                    JSON schemas generated from the models (skill, jd-analysis)
  supabase/migrations/          SQL for the Supabase tables (optional backend)
  tests/                        Pytest suite
  .env.example  .gitignore  requirements.txt  README.md
```