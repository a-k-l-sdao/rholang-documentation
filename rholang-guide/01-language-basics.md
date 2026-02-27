# Language Basics

## Processes and Channels

Everything in Rholang is a **process**. Processes communicate over **channels** (also called names). A channel is just a quoted process: `@process` turns a process into a name, `*name` turns a name back into a process.

```rholang
// Send the number 42 on the channel @"myChannel"
@"myChannel"!(42)

// Receive from that channel
for (@value <- @"myChannel") {
  // value is now 42
}
```

## `new` -- Creating Private Channels

`new` creates unforgeable (private) channels. Only code within the `new` block can access them.

```rholang
new myChannel in {
  myChannel!(42) |
  for (@x <- myChannel) {
    // x == 42
  }
}
```

Bind system contracts with URI syntax:

```rholang
new stdout(`rho:io:stdout`) in {
  stdout!("Hello World")
}
```

## Sending and Receiving

**Single send** -- consumed once:
```rholang
channel!(data)
```

**Persistent send** -- stays in the tuplespace forever:
```rholang
channel!!(data)
```

**Single receive** -- fires once then stops:
```rholang
for (@data <- channel) { ... }
```

**Persistent receive** -- fires for every message (replicated):
```rholang
for (@data <= channel) { ... }
```

## Parallel Composition

The `|` operator runs processes concurrently:

```rholang
new ch in {
  ch!(1) | ch!(2) | ch!(3) |
  for (@a <- ch; @b <- ch) {
    // a and b are any two of 1, 2, 3
  }
}
```

## Joins

Receive from multiple channels simultaneously:

```rholang
for (@x <- chan1; @y <- chan2) {
  // Fires when BOTH chan1 and chan2 have data
}
```

## Data Types

### Primitives

| Type | Examples |
|------|----------|
| Integer | `42`, `-1`, `0` |
| String | `"hello"`, `""` |
| Boolean | `true`, `false` |
| Nil | `Nil` |
| ByteArray | `"data".toByteArray()` |
| URI | `` `rho:io:stdout` `` |

### Collections

**Lists** (ordered):
```rholang
[]
[1, 2, 3]
[1, "mixed", true]

list.nth(0)          // first element
list.length()        // size
list.slice(1, 3)     // sublist [1..3)
list ++ [4, 5]       // concatenation
```

**Maps** (key-value):
```rholang
{}
{"name": "Alice", "age": 30}

map.get("name")              // "Alice" or Nil
map.getOrElse("x", "default")
map.set("name", "Bob")       // new map with updated key
map.delete("name")           // new map without key
map.contains("name")         // true/false
map.keys()                   // set of keys
map.size()                   // number of entries
```

**Sets** (unordered, unique):
```rholang
Set()
Set(1, 2, 3)

set.contains(2)     // true
set.add(4)           // new set
set.delete(2)        // new set
set.union(otherSet)
set.diff(otherSet)
set.size()
```

**Tuples** (ordered, fixed-size):
```rholang
(1,)           // single element (trailing comma required)
(1, 2, 3)
tuple.nth(0)   // first element
```

## Expressions

```rholang
// Arithmetic
1 + 2    3 - 1    2 * 3    10 / 3

// Comparison
x > 5    x >= 5    x < 5    x <= 5    x == 5    x != 5

// Logical
true and false    true or false    not true

// String concatenation
"hello" ++ " " ++ "world"
```

## Conditionals

```rholang
if (x > 0) {
  stdout!("positive")
} else {
  stdout!("non-positive")
}
```

The `else` branch is optional (defaults to `Nil`).

## Method Calls on Data

```rholang
"hello".length()            // 5
"hello".slice(1, 3)         // "el"
"abc".toByteArray()         // byte array
"4f2a".hexToBytes()         // bytes from hex
"text".toUtf8Bytes()        // UTF-8 encoded bytes
```

## Quoting and Unquoting

`@` quotes a process into a name. `*` unquotes a name back into a process.

```rholang
@42          // the name derived from process 42
@"hello"     // the name derived from process "hello"
*myChannel   // the process bound to name myChannel
```

Name equivalence: `@{10 + 2}` is the same name as `@12` because expressions are evaluated before quoting.

Inside `for` patterns, `@` destructures incoming data:

```rholang
for (@x <- ch) { ... }    // x binds to the value (process)
for (x <- ch) { ... }     // x binds to the name (channel)
```
