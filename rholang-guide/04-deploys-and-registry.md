# Deploys and the Registry

## Deploy Types

### Exploratory Deploy

Read-only. Free (no phlo). Can only call system contracts. Cannot trigger user-deployed contracts.

Use for: querying balances, reading state, debugging.

```bash
# Via rust client
cargo run -- exploratory-deploy -f query.rho -p 40402

# Via HTTP API
curl -X POST http://localhost:40403/api/explore-deploy \
  -H 'Content-Type: text/plain' \
  -d 'new stdout(`rho:io:stdout`) in { stdout!("hello") }'
```

**Limitation:** `rho:registry:lookup` resolves the URI, but you cannot trigger the looked-up contract in an exploratory deploy (it is a user contract). The lookup itself is a system call and works, but the `for (contract <- ch) { contract!(...) }` part won't fire because the registry returns data via the tuplespace which requires a real deploy.

### Full Deploy (deploy + propose)

State-changing. Costs phlo. Can call any contract.

Use for: deploying contracts, locking tokens, calling bridge methods.

```bash
# Deploy only (let heartbeat propose)
cargo run -- deploy -f contract.rho -p 40402 -b

# Full deploy (deploy + propose + wait for data)
cargo run -- full-deploy -f contract.rho -p 40402 -b
```

The `-b` flag sets phlo limit to 5 billion (needed for large contracts).

### Deploy + Heartbeat Pattern

When the node has `heartbeat.enabled = true`, the heartbeat proposer creates blocks automatically. Use `deploy` (not `full-deploy`) and poll for the result:

```bash
# 1. Deploy
DEPLOY_ID=$(cargo run -- deploy -f contract.rho -b -p 40402 | grep -oP 'Deploy ID: \K\S+')

# 2. Wait, then poll data-at-name
curl -s -X POST http://localhost:40403/api/data-at-name \
  -H 'Content-Type: application/json' \
  -d '{"depth":1,"name":{"UnforgDeploy":{"data":"'"$DEPLOY_ID"'"}}}'
```

## Deploy ID

Every deploy gets a unique ID (hex string). This is the signature of the deploy data.

To return results from a deploy, write to the `deployId` channel:

```rholang
new deployId(`rho:rchain:deployId`) in {
  // ... do work ...
  deployId!({"status": "ok", "result": 42})
}
```

The deployer retrieves results by querying `data-at-name` with `UnforgDeploy`:

```json
{
  "depth": 1,
  "name": { "UnforgDeploy": { "data": "<deploy-id-hex>" } }
}
```

## Registry URIs

Format: `rho:id:<zbase32-encoded-hash>`

Generated when you register a contract with `insertArbitrary`. The URI is a 34-character zbase32 encoding of a blake2b-256 hash with a 14-bit CRC checksum.

### Registering a Contract

```rholang
new insertArbitrary(`rho:registry:insertArbitrary`),
    myApi, uriCh in {

  // Define the contract
  contract myApi(@method, ret) = {
    match method {
      "ping" => { ret!("pong") }
      _      => { ret!({"error": "UnknownMethod"}) }
    }
  } |

  // Register it (bundle+ = write-only handle for callers)
  insertArbitrary!(bundle+{*myApi}, *uriCh) |

  for (@uri <- uriCh) {
    stdout!(["Registered at", uri])
    // uri looks like: rho:id:abc123def456...
  }
}
```

### Calling a Registered Contract

From a separate deploy:

```rholang
new deployId(`rho:rchain:deployId`),
    lookup(`rho:registry:lookup`), ch, ret in {
  lookup!(`rho:id:abc123def456...`, *ch) |
  for (api <- ch) {
    api!("ping", *ret) |
    for (@result <- ret) {
      deployId!(result)  // "pong"
    }
  }
}
```

### System Contract URIs

System contracts use shorthand URIs. When looking them up, they return a tuple `(timestamp, contract)`:

| Shorthand | Contract |
|-----------|----------|
| `rho:rchain:revVault` | REV token vault |
| `rho:rchain:multiSigRevVault` | Multi-signature vault |
| `rho:rchain:makeMint` | Token minting factory |
| `rho:rchain:authKey` | Auth key factory |
| `rho:rchain:pos` | Proof of Stake |
| `rho:lang:listOps` | List operations |
| `rho:lang:either` | Either type (error handling) |
| `rho:lang:nonNegativeNumber` | Non-negative number type |
| `rho:lang:treeHashMap` | Hash map data structure |

```rholang
// System contract pattern (note the tuple destructuring)
rl!(`rho:rchain:revVault`, *ch) |
for (@(_, RevVault) <- ch) {
  @RevVault!("findOrCreate", addr, *ret)
}
```

vs user contracts:

```rholang
// User contract pattern (no tuple)
lookup!(`rho:id:abc123...`, *ch) |
for (contract <- ch) {
  contract!("method", *ret)
}
```

## Phlo (Gas)

Every operation in a full deploy costs phlo. The deployer sets a phlo limit and price:

- **phloLimit**: Maximum phlo to spend (default 50,000; use `-b` flag for 5 billion)
- **phloPrice**: Price per unit (minimum 1)

If the deploy runs out of phlo, it reverts. Unused phlo is not charged.

Large contracts (like bridge.rho at 15KB) need high phlo limits.

## HTTP API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/deploy` | POST | Submit a signed deploy |
| `/api/explore-deploy` | POST | Run exploratory deploy (text/plain body) |
| `/api/data-at-name` | POST | Query data on a channel |
| `/api/blocks/{n}` | GET | Get last N blocks |
| `/api/status` | GET | Node status |

## Ports

| Port | Protocol | Purpose |
|------|----------|---------|
| 40400 | TCP | P2P protocol |
| 40401 | gRPC | External API |
| 40402 | gRPC | Internal/deploy API |
| 40403 | HTTP | HTTP/WebSocket API |
| 40404 | TCP | Peer discovery |
| 40405 | HTTP | Admin API |
