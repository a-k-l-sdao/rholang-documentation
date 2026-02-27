# System Contracts

System contracts are built into the node runtime and available via URI bindings. They are the only contracts accessible from exploratory deploys.

## I/O

### `rho:io:stdout`

Print to node stdout. Fire and forget.

```rholang
new stdout(`rho:io:stdout`) in {
  stdout!("hello") |
  stdout!(42) |
  stdout!({"key": "value"}) |
  stdout!(["a", "b", "c"])
}
```

### `rho:io:stdout:ack`

Print to stdout and receive an acknowledgment. Use this when ordering matters.

```rholang
new stdoutAck(`rho:io:stdout:ack`), ack in {
  stdoutAck!("first", *ack) |
  for (_ <- ack) {
    stdoutAck!("second", *ack) |
    for (_ <- ack) {
      stdoutAck!("third", *ack)
    }
  }
}
```

### `rho:io:stderr` / `rho:io:stderr:ack`

Same as stdout variants but writes to stderr.

## Cryptography

### `rho:crypto:sha256Hash`

```rholang
new sha(`rho:crypto:sha256Hash`), ret in {
  sha!("data".toByteArray(), *ret) |
  for (@hash <- ret) {
    // hash is a ByteArray
  }
}
```

### `rho:crypto:keccak256Hash`

Ethereum-compatible Keccak-256:

```rholang
new keccak(`rho:crypto:keccak256Hash`), ret in {
  keccak!("data".toByteArray(), *ret) |
  for (@hash <- ret) { ... }
}
```

### `rho:crypto:blake2b256Hash`

```rholang
new blake(`rho:crypto:blake2b256Hash`), ret in {
  blake!("data".toByteArray(), *ret) |
  for (@hash <- ret) { ... }
}
```

### `rho:crypto:ed25519Verify`

Verify an Ed25519 signature:

```rholang
new verify(`rho:crypto:ed25519Verify`), ret in {
  verify!(dataBytes, signatureBytes, publicKeyBytes, *ret) |
  for (@valid <- ret) {
    // valid is true or false
  }
}
```

### `rho:crypto:secp256k1Verify`

Verify a Secp256k1 (Bitcoin/Ethereum) signature:

```rholang
new verify(`rho:crypto:secp256k1Verify`), ret in {
  verify!(dataBytes, signatureBytes, publicKeyBytes, *ret) |
  for (@valid <- ret) {
    // valid is true or false
  }
}
```

## Block Data

### `rho:block:data`

Access metadata about the current block:

```rholang
new blockData(`rho:block:data`), ret in {
  blockData!(*ret) |
  for (@blockNumber, @timestamp, @sender <- ret) {
    // blockNumber: Int
    // timestamp: Int (millis since epoch)
    // sender: PublicKey bytes
  }
}
```

## Deploy Identity

### `rho:rchain:deployId`

The deploy ID channel. Write results here so the deployer can retrieve them:

```rholang
new deployId(`rho:rchain:deployId`) in {
  deployId!({"status": "ok", "value": 42})
}
```

The deployer calls `data-at-name` with `UnforgDeploy` to retrieve this value.

### `rho:rchain:deployerId`

The identity of the deployer (their public key). Used for authorization:

```rholang
new deployerId(`rho:rchain:deployerId`) in {
  // *deployerId is the unforgeable name representing the deployer
}
```

### `rho:rchain:deployerId:ops`

Get the raw public key bytes from a deployer ID:

```rholang
new deployerOps(`rho:rchain:deployerId:ops`),
    deployerId(`rho:rchain:deployerId`), ret in {
  deployerOps!("pubKeyBytes", *deployerId, *ret) |
  for (@pubKeyBytes <- ret) {
    // pubKeyBytes is a ByteArray
  }
}
```

## Registry

### `rho:registry:lookup`

Look up a contract by its URI:

```rholang
new lookup(`rho:registry:lookup`), ch in {
  lookup!(`rho:id:abc123...`, *ch) |
  for (contract <- ch) {
    contract!("someMethod", *retCh)
  }
}
```

For system contracts registered at genesis, the lookup returns a tuple `(timestamp, contract)`:

```rholang
new rl(`rho:registry:lookup`), RevVaultCh in {
  rl!(`rho:rchain:revVault`, *RevVaultCh) |
  for (@(_, RevVault) <- RevVaultCh) {
    @RevVault!("findOrCreate", revAddress, *vaultCh)
  }
}
```

### `rho:registry:insertArbitrary`

Register a contract and get a URI back:

```rholang
new insertArbitrary(`rho:registry:insertArbitrary`),
    myContract, uriCh in {
  contract myContract(@method, ret) = {
    match method {
      "hello" => { ret!("world") }
    }
  } |
  insertArbitrary!(bundle+{*myContract}, *uriCh) |
  for (@uri <- uriCh) {
    // uri is like rho:id:abc123...
    // Others can now lookup!(`rho:id:abc123...`) to use this contract
  }
}
```

### `rho:registry:insertSigned:secp256k1`

Register a contract with a cryptographic signature (used by system contracts at genesis):

```rholang
insertSigned!(publicKey, (timestamp, bundle+{*contract}, nonce), signature, *retCh)
```

## REV Addresses

### `rho:rev:address`

Generate and validate REV addresses:

```rholang
new revAddr(`rho:rev:address`), ret in {
  // From public key
  revAddr!("fromPublicKey", publicKeyBytes, *ret) |
  for (@address <- ret) { ... }
}
```

```rholang
// Validate an address
revAddr!("validate", "1111abc...", *ret) |
for (@result <- ret) {
  // result is Nil if valid, or error string
}
```

## REV Vault

### `rho:rchain:revVault`

The REV token wallet system. Look it up via registry:

```rholang
new rl(`rho:registry:lookup`), RevVaultCh in {
  rl!(`rho:rchain:revVault`, *RevVaultCh) |
  for (@(_, RevVault) <- RevVaultCh) {

    // Find or create a vault for an address
    new vaultCh in {
      @RevVault!("findOrCreate", "1111revAddress...", *vaultCh) |
      for (@(true, vault) <- vaultCh) {

        // Check balance
        new balCh in {
          @vault!("balance", *balCh) |
          for (@balance <- balCh) {
            stdout!(balance)  // integer balance
          }
        }
      }
    }
  }
}
```

**Vault methods:**

| Method | Arguments | Returns |
|--------|-----------|---------|
| `"findOrCreate"` | revAddress, retCh | `(true, vault)` or `(false, error)` |
| `"balance"` | retCh | integer |
| `"transfer"` | targetAddress, amount, authKey, retCh | `(true, Nil)` or `(false, error)` |
| `"deployerAuthKey"` | deployerId, retCh | auth key for transfers |

**Transfer example:**

```rholang
new rl(`rho:registry:lookup`), RevVaultCh,
    deployerId(`rho:rchain:deployerId`) in {
  rl!(`rho:rchain:revVault`, *RevVaultCh) |
  for (@(_, RevVault) <- RevVaultCh) {
    new vaultCh, authKeyCh, resultCh in {
      @RevVault!("findOrCreate", senderAddress, *vaultCh) |
      @RevVault!("deployerAuthKey", *deployerId, *authKeyCh) |
      for (@(true, vault) <- vaultCh; authKey <- authKeyCh) {
        @vault!("transfer", recipientAddress, amount, *authKey, *resultCh) |
        for (@result <- resultCh) {
          match result {
            (true, _)    => { stdout!("Transfer ok") }
            (false, err) => { stdout!(err) }
          }
        }
      }
    }
  }
}
```

## AI Services (Experimental)

These require `openai.enabled = true` in node config:

### `rho:ai:gpt4`

```rholang
new gpt4(`rho:ai:gpt4`), ret in {
  gpt4!("Describe a sunset", *ret) |
  for (@answer <- ret) {
    stdout!(answer)
  }
}
```

### `rho:ai:dalle3`

```rholang
new dalle3(`rho:ai:dalle3`), ret in {
  dalle3!("a cat in space", *ret) |
  for (@imageData <- ret) {
    stdout!(imageData)
  }
}
```

### `rho:ai:textToAudio`

```rholang
new tts(`rho:ai:textToAudio`), ret in {
  tts!("Hello world", *ret) |
  for (@audio <- ret) {
    stdout!("Audio generated")
  }
}
```

## Utility

### `rho:dev:null`

Discard messages (like `/dev/null`):

```rholang
new devnull(`rho:dev:null`) in {
  devnull!("ignored")
}
```

### `rho:error:abort`

Abort execution with an error.
