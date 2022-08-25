---
layout: post
title:  "Race Conditions Can Be Useful for Parallelism"
mathjax: true
---

The explosion of interest in parallel computing over the past few decades has
carried with it a fear and distrust of race conditions. People will say that
races are bad, that races cause bugs, and that races must be avoided.
Indeed, there are good reasons to avoid races, mostly because race conditions
can be difficult to reason about. But there are many aspects of programming
that are difficult to reason about. Are race conditions really all that
different?

With a bit of practice, I think you'll find that race conditions can
be disciplined, easy to reason about, and even useful. In this post, I'll
show a few examples where **we purposefully *create* race conditions, to
improve performance.**

Now, first, I need to get something out of the way:
**race conditions are not data races**. In the context of a language memory
model, a *data race* is typically defined as two conflicting concurrent
accesses which are not properly synchronized (e.g., "ordinary" loads and stores,
which the semantics of a language may allow to be reordered), leading to
incorrect behavior due to problems such as miscompilation or lack of atomicity.
Data races often have undefined behavior; in other words, data races are often
bugs, by definition.[^1]

Some people will say that data races are a subset of race conditions, but I
find this misleading. If a data race has undefined behavior, then you can't
prove that a data race is correct, because by definition, it isn't. In contrast,
**you can prove that a program with race conditions is correct**, by reasoning
carefully about all possible outcomes of the race.

## Parallel but not Concurrent

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


## Old Stuff Below

with one technique for controlling and reasoning about race conditions.
If you have ever attempted to design a lock-free data structure, you are likely
aware that there is a whole world of programming where programmers embrace,
rather than eschew, race conditions. I believe every programmer should at least
become familiar with this area of algorithm and data structure design. It's
valuable because it forces you to do away with any fears you might have
about race conditions. At a certain point, something clicks, and suddenly,
race conditions become just another thing that you are comfortable reasoning
about when trying to convince yourself that the code you wrote is correct.




instilled a sense of distrust and fear of
race conditions that I think we can push beyond, to empower all programmers.

The particular usefulness we will consider in this post, is for *performance*.

Essentially, a little non-determinism can go a long way.


-------------

-------------

[^1]: One recent exception is the OCaml memory model, which is capable of providing partial semantics to programs with data races. See [Bounding Data Races in Space and Time](https://kcsrk.info/papers/pldi18-memory.pdf), by Stephen Dolan, KC Sivaramakrishnan, and Anil Madhavapeddy.
