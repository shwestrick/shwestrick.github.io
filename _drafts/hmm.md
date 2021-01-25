---
layout: post
title:  "The Challenges Facing Parallel Functional Programming"
---

At CMU, my research has largely been centered around
parallel functional programming.

Functional programming is (in principle) an excellent vehicle for parallel
computing, because of its emphasis on immutability.
Any computation which does not modify existing data is inherently safe
for parallelism: it can be executed by anyone, at any time, and will behave
exactly the same every time.

Functional languages typically provide immutability by default, and some
even disallow mutation entirely.
Functional languages essentially take a strong stance on viewing mutability as
nothing more than a performance optimization or implementation detail.
In order to "change" something in a functional language, then, we don't
actually change anything. Instead, we allocate a new piece of data that is
slightly different.

One of the incredible strengths of functional programming is that,
in order for a programmer to reason about the correctness of their program,
they don't have to think about these details at all!
Allocation and de-allocation is completely implicit, handled by the compiler
and garbage collector.
Contrast this with e.g. C++, where the programmer must explicitly allocate
and de-allocate data with `new` and `delete` (okay, yes, C++ is able to
mechanically insert some of the appropriate commands in the right places
via move and copy semantics, but this doesn't change the fact that you
have to reason about these things in order to guarantee that your program
is correct).
Similarly, in languages such as Java or Go which are garbage-collected,
although de-allocation is implicit, allocation is still explicit.
Rust also has automatic de-allocation, but explicit allocation.

But functional programming's greatest strength has also long been its
greatest weakness.
The tendency to allocate new data (rather than modify existing data in-place)
causes functional languages to allocate at a much higher rate than
languages such as Java, C++, or Go.
Essentially, functional programming requires extremely efficient automatic
memory management in order to be efficient.

For sequential functional languages, this problem has mostly been solved
through the combination of a number of techniques:
  * Better compilation strategies, to reduce the number of allocations.
  * Bump allocation, which makes individual allocations extremely fast.
  * Generational GC, which quickly cleans up short-lived data.
  * Compactifying GC, to eliminate fragmentation.

In the world of parallelism, however,


One of the most prevalent GC designs for parallel functional languages is
based on a two-level structure.
At the top level, there is a "global" heap which is shared amongst all
processors.
Each processor then has its own processor-local heap.

One of the biggest issues with this design, however, is that it requires
promotions in order to share data between processors.
For any reasonable scheduler, these operations are much too frequent!

HMM...

{% comment %}
Functional programming languages---such as
OCaml, Standard ML, F#, Elm, Haskell, and many
others---typically allocate much more data than other
languages.
The reason for this is not-so-much due to using functions as
data, but rather due to the emphasis on immutability.
{% endcomment %}
