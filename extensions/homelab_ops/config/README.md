# Configuration

`inventory.json` and `policy.json` are intentionally ignored by Git because they may contain private hostnames, addresses and local policy.

Start from the example files:

```bash
cp inventory.example.json inventory.json
cp policy.example.json policy.json
chmod 600 inventory.json policy.json
```

Keep SSH private keys and approval secrets outside this directory and outside the repository.
