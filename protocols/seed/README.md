# Seed clinical protocols

These Markdown files are illustrative seed documents used by the
RAG indexer when no real PDF corpus is available. They are NOT actual
FDA or ANSM monographs; they follow the structure of a hospital
substitution protocol and cite ATC codes correctly so the retriever can
be exercised end-to-end.

For a realistic demo, drop real FDA SPL PDFs or ANSM RCP PDFs under
`protocols/raw/` and re-run `make index-rag`.
