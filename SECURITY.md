# Security

Never commit API keys, wallet private keys, Base MCP tokens, Sibyl credentials, `.env` files, or the local SQLite memory database.

Vesper is designed so Base MCP holds no private key. Transactions should be prepared through Base MCP and approved by the operator in Base Account. Use a dedicated wallet with minimal funds for demonstrations.

If a secret is accidentally committed, rotate it immediately. Removing the file in a later commit does not remove it from Git history.
