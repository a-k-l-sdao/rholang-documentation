# Standard Library

These contracts are deployed at genesis and available via `rho:registry:lookup`. They return a tuple `(timestamp, contract)`.

## NonNegativeNumber

A number that cannot go below zero. Used internally by MakeMint for token balances.

```rholang
rl!(`rho:lang:nonNegativeNumber`, *NNNCh) |
for (@(_, NonNegativeNumber) <- NNNCh) {
  new valueCh in {
    @NonNegativeNumber!(100, *valueCh) |  // create with initial value 100
    for (nnn <- valueCh) {
      new retCh in {
        nnn!("value", *retCh) |          // get: returns 100
        for (@v <- retCh) { ... }
      } |
      new retCh in {
        nnn!("add", 50, *retCh) |        // add: returns true, value is now 150
        for (@ok <- retCh) { ... }
      } |
      new retCh in {
        nnn!("sub", 30, *retCh) |        // sub: returns true, value is now 120
        for (@ok <- retCh) { ... }        // returns false if would go negative
      }
    }
  }
}
```

## MakeMint

Create custom token systems with purses:

```rholang
rl!(`rho:rchain:makeMint`, *MakeMintCh) |
for (@(_, MakeMint) <- MakeMintCh) {
  new mintCh in {
    @MakeMint!(*mintCh) |
    for (mint <- mintCh) {

      // Create a purse with 1000 tokens
      new purseCh in {
        mint!("makePurse", 1000, *purseCh) |
        for (purse <- purseCh) {

          // Check balance
          new balCh in {
            purse!("getBalance", *balCh) |
            for (@balance <- balCh) {
              // balance == 1000
            }
          } |

          // Split off 200 tokens into a new purse
          new splitCh in {
            purse!("split", 200, *splitCh) |
            for (@result <- splitCh) {
              // result is (true, newPurse) or (false, error)
            }
          }
        }
      }
    }
  }
}
```

## AuthKey

Create unforgeable authentication tokens:

```rholang
rl!(`rho:rchain:authKey`, *AuthKeyCh) |
for (@(_, AuthKey) <- AuthKeyCh) {

  // Create a key with a secret shape
  new secret in {
    new keyCh in {
      @AuthKey!("make", bundle0{*secret}, *keyCh) |
      for (key <- keyCh) {

        // Verify the key later
        new validCh in {
          @AuthKey!("check", *key, bundle0{*secret}, *validCh) |
          for (@isValid <- validCh) {
            // isValid == true
          }
        }
      }
    }
  }
}
```

## ListOps

Functional list operations:

```rholang
rl!(`rho:lang:listOps`, *ListOpsCh) |
for (@(_, ListOps) <- ListOpsCh) {
  new retCh in {
    // Available methods:
    @ListOps!("map", [1, 2, 3], mappingContract, *retCh)
    @ListOps!("filter", [1, 2, 3], predicateContract, *retCh)
    @ListOps!("fold", [1, 2, 3], initialValue, foldContract, *retCh)
  }
}
```

## TreeHashMap

Efficient hash map for large datasets. Uses a trie structure with configurable depth:

```rholang
rl!(`rho:lang:treeHashMap`, *TreeHashMapCh) |
for (@(_, TreeHashMap) <- TreeHashMapCh) {

  // Initialize a new map with depth 2 (4 buckets)
  new mapCh in {
    @TreeHashMap!("init", 2, *mapCh) |
    for (map <- mapCh) {

      // Set a key
      new ackCh in {
        @TreeHashMap!("set", *map, "myKey", "myValue", *ackCh) |
        for (_ <- ackCh) {

          // Get a key
          new retCh in {
            @TreeHashMap!("get", *map, "myKey", *retCh) |
            for (@value <- retCh) {
              // value == "myValue"
            }
          }
        }
      }
    }
  }
}
```

**Methods:**

| Method | Arguments | Description |
|--------|-----------|-------------|
| `"init"` | depth, retCh | Create map with 2^depth buckets |
| `"set"` | map, key, value, ackCh | Insert or update |
| `"get"` | map, key, retCh | Lookup (returns Nil if missing) |
| `"fastUnsafeGet"` | map, key, retCh | Fast lookup (may have race conditions) |
| `"contains"` | map, key, retCh | Returns true/false |

## Either

Error handling with success/failure values:

```rholang
rl!(`rho:lang:either`, *EitherCh) |
for (@(_, Either) <- EitherCh) {
  new retCh in {
    @Either!("fromNillableError <-", resultChannel, *retCh) |
    for (@result <- retCh) {
      match result {
        (true, value) => { /* success */ }
        (false, err)  => { /* error */ }
      }
    }
  }
}
```

## Proof of Stake

Validator operations:

```rholang
rl!(`rho:rchain:pos`, *PoSCh) |
for (@(_, PoS) <- PoSCh) {
  new deployerId(`rho:rchain:deployerId`), retCh in {
    // Bond as validator
    @PoS!("bond", *deployerId, bondAmount, *retCh) |
    for (@(_, message) <- retCh) {
      stdout!(message)
    }
  }
}
```
