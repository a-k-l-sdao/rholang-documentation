# Contracts and Patterns

## Contracts

A `contract` is syntactic sugar for a persistent receive. It fires for every incoming message:

```rholang
new greet in {
  contract greet(@name, ret) = {
    ret!("Hello, " ++ name)
  } |

  new r1, r2 in {
    greet!("Alice", *r1) |
    greet!("Bob", *r2) |
    for (@a <- r1; @b <- r2) {
      // a == "Hello, Alice", b == "Hello, Bob"
    }
  }
}
```

This is equivalent to:

```rholang
for (@name, ret <= greet) { ret!("Hello, " ++ name) }
```

## Pattern Matching

### match Expression

```rholang
match value {
  0       => { stdout!("zero") }
  x       => { stdout!(x) }         // binds x
  _       => { stdout!("default") } // wildcard, no binding
}
```

### Matching in `for`

```rholang
for (@{"status": "ok", "data": data} <- resultCh) {
  // Only fires if the map has status "ok"
  // data is bound to the value of the "data" key
}
```

### List Destructuring

```rholang
match myList {
  []            => { stdout!("empty") }
  [head ...tail] => { stdout!(head) }  // head + rest
}
```

### Logical Connectives

```rholang
// AND: both must match
for (@{x /\ Int} <- ch) { ... }  // x is bound AND must be an Int

// OR: either can match (no variable binding allowed)
for (@{Int \/ String} <- ch) { ... }
```

### Type Guards

```rholang
for (@Int <- ch) { ... }      // only matches integers
for (@String <- ch) { ... }   // only matches strings
for (@Bool <- ch) { ... }     // only matches booleans
```

### Important: No Arithmetic in Patterns

Patterns are structural. This does NOT work:

```rholang
// WRONG -- will not match @15
for (@{x + 5} <- ch) { ... }
```

## Mutable State

Rholang has no variables. Simulate mutable state with a channel that holds the current value:

```rholang
new MakeCell in {
  contract MakeCell(@init, get, set) = {
    new valueCh in {
      valueCh!(init) |
      contract get(ret) = {
        for (@value <- valueCh) {
          valueCh!(value) |  // put it back
          ret!(value)
        }
      } |
      contract set(@newValue, ack) = {
        for (_ <- valueCh) {
          valueCh!(newValue) |
          ack!(true)
        }
      }
    }
  }
}
```

The pattern: read the channel (consuming the value), process it, then put the value back (or a new value).

## Sequential Execution with Acknowledgments

Rholang is concurrent by default. To force ordering, use acknowledgment channels:

```rholang
new ack in {
  stdout!("first") |
  stdoutAck!("second", *ack) |
  for (_ <- ack) {
    stdout!("third -- guaranteed after second")
  }
}
```

Or chain with `rho:io:stdout:ack`:

```rholang
new ack, stdoutAck(`rho:io:stdout:ack`) in {
  stdoutAck!("step 1", *ack) |
  for (_ <- ack) {
    stdoutAck!("step 2", *ack) |
    for (_ <- ack) {
      stdout!("step 3")
    }
  }
}
```

## Select Statement

Choose between alternative message patterns:

```rholang
select {
  case @value <- chan1 => { stdout!(value) }
  case @value <- chan2 => { stdout!(value) }
}
```

Fires whichever channel has data first. Useful for implementing cells with get/set:

```rholang
contract Cell(get, set, state) = {
  select {
    case ret <- get; @v <- state => {
      ret!(v) | state!(v) | Cell!(*get, *set, *state)
    }
    case @newVal <- set; _ <- state => {
      state!(newVal) | Cell!(*get, *set, *state)
    }
  }
}
```

## Iteration

Recursion is the only way to loop:

```rholang
new loop in {
  contract loop(@list) = {
    match list {
      []            => { Nil }
      [head ...tail] => {
        stdout!(head) |
        loop!(tail)
      }
    }
  } |
  loop!([1, 2, 3, 4, 5])
}
```
