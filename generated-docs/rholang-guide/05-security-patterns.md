# Security Patterns

Rholang uses capability-based security. Access to a channel is authority to use it. If you don't have the channel name, you can't interact with it.

## Bundles

Control read/write access to channels:

```rholang
bundle+{*ch}   // write-only: can send, cannot receive
bundle-{*ch}   // read-only: can receive, cannot send
bundle0{*ch}   // opaque: cannot read or write (used to hide internals)
bundle{*ch}    // full access: both read and write
```

### Write-only API

Expose a contract so callers can send requests but not eavesdrop:

```rholang
new insertArbitrary(`rho:registry:insertArbitrary`),
    myService, uriCh in {
  contract myService(@request, ret) = {
    ret!("response")
  } |
  // Callers can only send to myService, not intercept others' requests
  insertArbitrary!(bundle+{*myService}, *uriCh)
}
```

## Facets Pattern

Provide different views of the same resource:

```rholang
new makeCell in {
  contract makeCell(@init, readOnly, readWrite) = {
    new valueCh in {
      valueCh!(init) |

      // Read-only facet
      contract readOnly(ret) = {
        for (@v <- valueCh) {
          valueCh!(v) | ret!(v)
        }
      } |

      // Read-write facet
      contract readWrite(@newVal, ack) = {
        for (_ <- valueCh) {
          valueCh!(newVal) | ack!(true)
        }
      }
    }
  } |

  new get, set in {
    makeCell!(0, *get, *set) |
    // Give bundle+{*get} to untrusted code (read-only access)
    // Keep *set private (only owner can write)
  }
}
```

## Attenuating Forwarder

Limit what an untrusted party can do with a capability:

```rholang
// Allow only "read" method, block everything else
new attenuated in {
  contract attenuated(@method, ret) = {
    if (method == "read") {
      fullAccess!(method, *ret)
    } else {
      ret!({"error": "unauthorized"})
    }
  }
}
```

## Revocable Forwarder

Grant access that can be revoked later:

```rholang
new MakeRevokable in {
  contract MakeRevokable(target, ret) = {
    new port, kill, flagCh in {
      flagCh!(true) |
      ret!(*port, *kill) |

      contract port(@msg, ret) = {
        for (@active <- flagCh) {
          flagCh!(active) |
          if (active) {
            target!(msg, *ret)
          } else {
            ret!({"error": "revoked"})
          }
        }
      } |

      for (_ <- kill; _ <- flagCh) {
        flagCh!(false)
      }
    }
  }
}
```

Usage:

```rholang
new portCh, killCh in {
  MakeRevokable!(realService, *portCh) |
  for (port, kill <- portCh) {
    // Give *port to untrusted code
    // Later, revoke: kill!(Nil)
  }
}
```

## Logging Forwarder

Wrap a capability to log all access:

```rholang
new MakeLogging in {
  contract MakeLogging(target, logCh, ret) = {
    new proxy in {
      ret!(*proxy) |
      contract proxy(@msg, ret) = {
        logCh!({"action": msg, "timestamp": "now"}) |
        target!(msg, *ret)
      }
    }
  }
}
```

## Sealer/Unsealer Pattern

Like public/private keys but using unforgeable names. Only the holder of the unsealer can read sealed values:

```rholang
new MakeSealerUnsealer in {
  contract MakeSealerUnsealer(ret) = {
    new mapCh, nonceCh in {
      mapCh!({}) | nonceCh!(0) |

      new sealer, unsealer in {
        ret!(*sealer, *unsealer) |

        contract sealer(@value, ret) = {
          for (@nonce <- nonceCh; @map <- mapCh) {
            nonceCh!(nonce + 1) |
            mapCh!(map.set(nonce, value)) |
            ret!(nonce)  // return ticket
          }
        } |

        contract unsealer(@ticket, ret) = {
          for (@map <- mapCh) {
            mapCh!(map) |
            ret!(map.get(ticket))
          }
        }
      }
    }
  }
}
```

## Authorization with AuthKey

The standard pattern for authorized operations (used by RevVault):

```rholang
new rl(`rho:registry:lookup`), AuthKeyCh in {
  rl!(`rho:rchain:authKey`, *AuthKeyCh) |
  for (@(_, AuthKey) <- AuthKeyCh) {

    // Create a key for a specific shape
    new shapeCh in {
      @AuthKey!("make", bundle0{*shapeCh}, *retCh) |
      for (authKey <- retCh) {
        // authKey can be verified later with:
        // @AuthKey!("check", *authKey, bundle0{*shapeCh}, *validCh)
      }
    }
  }
}
```
