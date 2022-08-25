---
layout: post
title:  "Race Conditions Can Be Useful for Parallelism"
mathjax: true
---

The explosion of interest in parallel computing over the past few decades has
carried with it a fear and distrust of race conditions. People will say that
races are bad, that races cause bugs, and that races must be avoided. Indeed,
race conditions can be difficult to reason about, and if you do have a bug,
then race conditions can make it difficult to debug. But there's nothing
inherently bad about a race condition, if you can prove that the resulting
program is correct.

With a bit of practice, I think you'll find that race
conditions can be disciplined, easy to reason about, and even useful. In this
post, I'll show a few examples where
**we purposefully *create* race conditions, to improve performance.**
Roughly speaking, the gist is that a small amount of non-determinism can be
useful for avoiding unnecessary (and expensive) synchronization.

Now, first, let me emphasize: **I'm not talking about data races**.
Data races are typically bugs, by definition.[^1]
Instead, I'm talking about how to utilize atomic operations,
such as compare-and-swap, test-and-set, fetch-and-add, etc., as well as
atomic loads and stores.

If you have ever attempted to design a lock-free data structure, you are likely
aware that there is a whole world of programming where programmers embrace,
rather than eschew, race conditions. I believe every programmer should at least
become familiar with this area of algorithm and data-structure design. It's
valuable because it forces you to do away with any fears you might have
about race conditions. At a certain point, something clicks, and suddenly,
race conditions become just another thing that you are comfortable reasoning
about when trying to convince yourself that the code you wrote is correct.

## Parallel but not Concurrent

The starting point for this discussion is programs which are parallel,
but not concurrent.

There are some circumstances where race conditions are fundamental and
unavoidable. For example, if you are developing an interactive website, then
you don't know when a button might be pressed, and you have no choice but to
consider questions such as: what happens if the button is pressed before the
page finishes loading? Alternatively, if you are writing

This is the world of *concurrent programming*, where race conditions are simply
a fact of life. Programmers in this world are familiar with using techniques
like locks to control race conditions and make them easier to reason about.

Let's pivot away from concurrency, and instead consider *parallel programming*.
The goal of parallelism is to do a task faster by executing many subtasks
simultaneously. This is different from concurrency, because it is possible to
write programs which have parallelism and yet are *free from race conditions*.


-------------

-------------

[^1]: In the context of a language memory model, a *data race* is typically defined as two conflicting concurrent accesses which are not "properly synchronized" (e.g., non-atomic loads and stores, which the language semantics may allow to be reordered, optimized away, etc). Data races can lead to incorrect behavior due to miscompilation or lack of atomicity. For this reason, data races are often considered undefined behavior. In other words, in many languages, data races are essentially bugs by definition. One recent exception is the OCaml memory model, which is capable of providing partial semantics to programs with data races. See [Bounding Data Races in Space and Time](https://kcsrk.info/papers/pldi18-memory.pdf), by Stephen Dolan, KC Sivaramakrishnan, and Anil Madhavapeddy.
