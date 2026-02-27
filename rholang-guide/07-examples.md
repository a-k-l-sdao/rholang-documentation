# Complete Working Examples

## 1. Hello World

The simplest deploy. Prints to the node's stdout:

```rholang
new stdout(`rho:io:stdout`) in {
  stdout!("Hello, Shard!")
}
```

Deploy with:

```bash
cargo run -- deploy -f hello.rho -p 40402
```

Or as an exploratory deploy (free, read-only):

```bash
cargo run -- exploratory-deploy -f hello.rho -p 40402
```

## 2. Return Channel (Request/Response)

Define a contract that takes arguments and returns a result through a callback channel:

```rholang
new stdout(`rho:io:stdout`), ack in {
  contract multiply(@a, @b, ret) = { ret!(a * b) } |
  multiply!(3, 4, *ack) |
  for (@res <- ack) { stdout!(res) }
}
```

Output: `12`

The pattern: the caller creates a fresh channel (`ack`), passes `*ack` (the name) to the contract, and waits on it with `for`.

## 3. Pattern Matching

Branch on values using `match`:

```rholang
new stdout(`rho:io:stdout`) in {
  contract check(@x) = {
    match x {
      0 => { stdout!("zero") }
      1 => { stdout!("one") }
      _ => { stdout!("other") }
    }
  } |
  check!(1) |
  check!(0) |
  check!(42)
}
```

All three calls run concurrently. Output order is non-deterministic.

## 4. Recursion (Looping)

There are no for-loops. Use recursive contracts:

```rholang
new stdout(`rho:io:stdout`) in {
  contract counter(@n) = {
    if (n <= 0) { stdout!("Done") } else {
      stdout!(n) |
      counter!(n - 1)
    }
  } |
  counter!(3)
}
```

Output (order may vary): `3`, `2`, `1`, `Done`

## 5. Concurrent Processes

The `|` operator runs processes in parallel:

```rholang
new stdout(`rho:io:stdout`) in {
  contract printer(@msg) = { stdout!(msg) } |
  printer!("A") | printer!("B") | printer!("C")
}
```

All three messages print concurrently. There is no guaranteed ordering.

## 6. Returning Results via deployId

To get data back from a full deploy, write to the `deployId` channel. The deployer retrieves it by querying `data-at-name`:

```rholang
new deployId(`rho:rchain:deployId`),
    stdout(`rho:io:stdout`) in {
  deployId!({"status": "ok", "value": 42}) |
  stdout!("Result sent to deployId")
}
```

Retrieve the result:

```bash
# 1. Deploy and get the deploy ID
DEPLOY_ID=$(cargo run -- deploy -f contract.rho -b -p 40402 | grep -oP 'Deploy ID: \K\S+')

# 2. Poll for the result (after block is proposed)
curl -s -X POST http://localhost:40403/api/data-at-name \
  -H 'Content-Type: application/json' \
  -d '{"depth":1,"name":{"UnforgDeploy":{"data":"'"$DEPLOY_ID"'"}}}'
```

## 7. Register a Contract in the Registry

Deploy a contract once, then call it from other deploys by its URI:

### Deploy 1: Register

```rholang
new insertArbitrary(`rho:registry:insertArbitrary`),
    deployId(`rho:rchain:deployId`),
    stdout(`rho:io:stdout`),
    calculator in {

  contract calculator(@method, @a, @b, ret) = {
    match method {
      "add" => { ret!(a + b) }
      "mul" => { ret!(a * b) }
      _     => { ret!({"error": "UnknownMethod"}) }
    }
  } |

  insertArbitrary!(bundle+{*calculator}, *deployId) |
  for (@uri <- deployId) {
    stdout!(["Calculator registered at", uri])
  }
}
```

Save the URI from the output (e.g., `rho:id:abc123...`).

### Deploy 2: Call it

```rholang
new deployId(`rho:rchain:deployId`),
    lookup(`rho:registry:lookup`),
    calcCh, retCh in {
  lookup!(`rho:id:abc123...`, *calcCh) |
  for (calc <- calcCh) {
    calc!("add", 10, 32, *retCh) |
    for (@result <- retCh) {
      deployId!(result)  // 42
    }
  }
}
```

## 8. Persist Data Across Deploys

Store a value in the registry so it survives across blocks:

```rholang
new insertArbitrary(`rho:registry:insertArbitrary`),
    stdout(`rho:io:stdout`),
    deployId(`rho:rchain:deployId`),
    dataCh in {
  dataCh!("Persistent Data") |
  insertArbitrary!(*dataCh, *deployId) |
  for (@uri <- deployId) {
    stdout!(uri)
  }
}
```

Later, look it up:

```rholang
new lookup(`rho:registry:lookup`), ch in {
  lookup!(`rho:id:<uri-from-above>`, *ch) |
  for (@data <- ch) {
    // data == "Persistent Data"
  }
}
```

## 9. Mutable State Cell

A reusable get/set cell using a channel as storage:

```rholang
new stdout(`rho:io:stdout`), MakeCell in {
  contract MakeCell(@init, get, set) = {
    new valueCh in {
      valueCh!(init) |
      contract get(ret) = {
        for (@v <- valueCh) {
          valueCh!(v) | ret!(v)
        }
      } |
      contract set(@newVal, ack) = {
        for (_ <- valueCh) {
          valueCh!(newVal) | ack!(true)
        }
      }
    }
  } |

  new get, set, ack in {
    MakeCell!(0, *get, *set) |
    // Set value to 42
    set!(42, *ack) |
    for (_ <- ack) {
      // Read value back
      get!(*ack) |
      for (@v <- ack) {
        stdout!(["value is", v])  // ["value is", 42]
      }
    }
  }
}
```

## 10. REV Balance Check

Query a REV vault balance (works as exploratory deploy):

```rholang
new rl(`rho:registry:lookup`),
    stdout(`rho:io:stdout`),
    RevVaultCh in {
  rl!(`rho:rchain:revVault`, *RevVaultCh) |
  for (@(_, RevVault) <- RevVaultCh) {
    new vaultCh in {
      @RevVault!("findOrCreate", "1111your_rev_address_here", *vaultCh) |
      for (@(true, vault) <- vaultCh) {
        new balCh in {
          @vault!("balance", *balCh) |
          for (@balance <- balCh) {
            stdout!(["Balance:", balance])
          }
        }
      }
    }
  }
}
```

## 11. REV Transfer

Transfer REV between addresses (requires a full deploy, not exploratory):

```rholang
new rl(`rho:registry:lookup`),
    deployerId(`rho:rchain:deployerId`),
    deployId(`rho:rchain:deployId`),
    stdout(`rho:io:stdout`),
    RevVaultCh in {
  rl!(`rho:rchain:revVault`, *RevVaultCh) |
  for (@(_, RevVault) <- RevVaultCh) {
    new vaultCh, authKeyCh, resultCh in {
      @RevVault!("findOrCreate", "1111senderAddress", *vaultCh) |
      @RevVault!("deployerAuthKey", *deployerId, *authKeyCh) |
      for (@(true, vault) <- vaultCh; authKey <- authKeyCh) {
        @vault!("transfer", "1111recipientAddress", 500, *authKey, *resultCh) |
        for (@result <- resultCh) {
          match result {
            (true, _)    => { deployId!("Transfer ok") }
            (false, err) => { deployId!(err) }
          }
        }
      }
    }
  }
}
```

## 12. Querying a Deployed Contract

A common pattern: look up a registered contract by URI and call a method:

```rholang
new deployId(`rho:rchain:deployId`),
    lookup(`rho:registry:lookup`),
    stdout(`rho:io:stdout`),
    bridgeCh in {
  lookup!(`rho:id:your_contract_uri_here`, *bridgeCh) |
  for (bridge <- bridgeCh) {
    new retCh in {
      bridge!("getNonce", *retCh) |
      for (@result <- retCh) {
        stdout!(["nonce", result]) |
        deployId!(result)
      }
    }
  }
}
```

Deploy and retrieve the result:

```bash
DEPLOY_ID=$(cargo run -- deploy -f get_nonce.rho -b -p 40402 | grep -oP 'Deploy ID: \K\S+')

# Wait for block, then poll
curl -s -X POST http://localhost:40403/api/data-at-name \
  -H 'Content-Type: application/json' \
  -d '{"depth":1,"name":{"UnforgDeploy":{"data":"'"$DEPLOY_ID"'"}}}'
```

## 13. Sequential Operations with Acknowledgments

Force ordering in a concurrent language:

```rholang
new stdoutAck(`rho:io:stdout:ack`),
    stdout(`rho:io:stdout`),
    ack in {
  stdoutAck!("Step 1: Initialize", *ack) |
  for (_ <- ack) {
    stdoutAck!("Step 2: Process", *ack) |
    for (_ <- ack) {
      stdoutAck!("Step 3: Finalize", *ack) |
      for (_ <- ack) {
        stdout!("All steps complete")
      }
    }
  }
}
```

Guaranteed output order: Step 1, Step 2, Step 3, All steps complete.

## 14. Multi-Method Contract (Object Pattern)

Expose multiple methods on a single channel using pattern matching on the first argument:

```rholang
new insertArbitrary(`rho:registry:insertArbitrary`),
    deployId(`rho:rchain:deployId`),
    stdout(`rho:io:stdout`),
    tokenService in {

  new totalCh, nonceCh in {
    totalCh!(0) | nonceCh!(0) |

    contract tokenService(@method, @arg, ret) = {
      match method {
        "lock" => {
          for (@total <- totalCh; @nonce <- nonceCh) {
            totalCh!(total + arg) |
            nonceCh!(nonce + 1) |
            ret!({"status": "ok", "nonce": nonce, "total": total + arg})
          }
        }
        "getTotal" => {
          for (@total <- totalCh) {
            totalCh!(total) |
            ret!(total)
          }
        }
        "getNonce" => {
          for (@nonce <- nonceCh) {
            nonceCh!(nonce) |
            ret!(nonce)
          }
        }
        _ => {
          ret!({"error": "UnknownMethod"})
        }
      }
    } |

    insertArbitrary!(bundle+{*tokenService}, *deployId) |
    for (@uri <- deployId) {
      stdout!(["TokenService registered at", uri])
    }
  }
}
```

## 15. Hashing and Signature Verification

Use built-in crypto system contracts:

```rholang
new sha256(`rho:crypto:sha256Hash`),
    keccak(`rho:crypto:keccak256Hash`),
    stdout(`rho:io:stdout`),
    ret1, ret2 in {
  sha256!("hello".toByteArray(), *ret1) |
  keccak!("hello".toByteArray(), *ret2) |
  for (@shaHash <- ret1; @kecHash <- ret2) {
    stdout!(["SHA-256:", shaHash]) |
    stdout!(["Keccak-256:", kecHash])
  }
}
```

Verify an Ed25519 signature:

```rholang
new verify(`rho:crypto:ed25519Verify`), ret in {
  verify!(dataBytes, signatureBytes, publicKeyBytes, *ret) |
  for (@valid <- ret) {
    if (valid) {
      // signature is valid
    } else {
      // signature is invalid
    }
  }
}
```

## Tips and Common Pitfalls

1. **Exploratory deploys are read-only.** They can call system contracts (`rho:io:stdout`, `rho:registry:lookup`, etc.) but cannot trigger user-deployed contracts. Use `full-deploy` or `deploy` + propose for state changes.

2. **Always consume and replace state.** When reading from a state channel, put the value back:
   ```rholang
   for (@v <- stateCh) { stateCh!(v) | /* use v */ }
   ```
   If you forget `stateCh!(v)`, the value is gone forever.

3. **Use `-b` for large contracts.** The default phlo limit (50,000) is too low for anything beyond trivial contracts. The `-b` flag sets it to 5 billion.

4. **Registry URIs use backticks, not quotes.**
   ```rholang
   lookup!(`rho:id:abc123...`, *ch)   // correct
   lookup!("rho:id:abc123...", *ch)   // WRONG -- treated as a string, not a URI
   ```

5. **System contracts return tuples.** When looking up system contracts (like `rho:rchain:revVault`), destructure the tuple:
   ```rholang
   for (@(_, RevVault) <- ch) { ... }  // system contract
   for (contract <- ch) { ... }         // user contract
   ```

6. **No big integers.** Rholang integers have limits. If bridging from Ethereum, convert wei to whole tokens before embedding in Rholang code.

7. **Order is not guaranteed.** Processes separated by `|` run concurrently. Use acknowledgment channels (`rho:io:stdout:ack`) or join patterns (`for (a <- ch1; b <- ch2)`) to enforce ordering.
