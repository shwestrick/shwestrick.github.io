---
layout: post
title:  "From ML to Multicore"
mathjax: true
---

No, not that ML. I'm talking about the programming language! Granted, the
name "ML" (originally "Meta Language") is a terrible name.

The question is simple: how do we take high-level code like the following,
and turn it into a parallel program that is as fast as hand-optimized
C?

```sml
(** Numerical integration of function f in the interval [a,b],
  * using a Riemann sum of N points.
  *)
fun integrate(f, a, b, N) =
  let
    val rectWidth = (b-a) / Real.fromInt(N)
    val a' = a + rectWidth/2.0
    val points = tabulate(N, fn i => f(a' + Real.fromInt(i) * rectWidth))
  in
    rectWidth * reduce(points, fn (x,y) => x+y)
  end
```

Understanding how this works covers a whole range of topics:
* Library design. Use well-known technique: represent a sequence by a function
that computes its elements. Makes it possible to avoid generating an
intermediate array.
* Parallel algorithm design. Compute `reduce` efficiently
with divide-and-conquer.
* Granularity control. Switch to sequential alternative below threshold.
* Compiling higher-order, typed, functional language. Handling higher-order
functions by closure conversion and polymorphism with monomorphisization.
* Scheduling by work-stealing.
* Lightweight threading. Heap-allocated call-stacks.
* Bump-allocation.
* Parallel GC.
