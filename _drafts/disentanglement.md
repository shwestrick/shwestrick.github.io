---
layout: post
title:  "Disentanglement: The Inherent Memory Structure of Parallel Programs"
---

Memory allocation is one of the most basic elements of modern programming.
Rather than access and modify memory at will, we choose to restrict ourselves
to a discipline of explicitly acquiring new memory and later releasing that
memory when we are finished using it. This discipline makes it possible
to reason locally about the correctness of our code, and avoid a slew of
possible memory errors.

When a program allocates a new piece of memory, that new piece of memory
is added to the program's ***heap***. It's not clear who coined the term
"heap", but presumably they chose the name to suggest a *lack of structure*.
(especially in comparison to, say, the "stack", which feels quite orderly in
comparison). And indeed to this day, heaps continue to show no apparent
structure.
(FOOTNOTE: one notable exception: the generational hypothesis.)
The best mental model for the heap of a typical
C++/Java/Go/Python/Lisp/ML/Haskell/etc program is just a messy pile
of garbage (pun intended).

When parallelism began to enter into the conversation,
language designers adapted to the demands of parallelism by adjusting the
behavior of allocation to be efficient in parallel, for example by giving each
thread its own "free list" (of "free" segments of memory, that are available
for use). This essentially solves the problem of growing the heap quickly, but
doesn't solve the problem of shrinking it.

For languages with garbage collection, the apparent lack of structure in the
heap poses a big problem.
Parallel garbage collectors have their hands tied, limited to viewing
the problem as essentially an unstructured graph reachability problem.
This all fine and good, except for the fact that after decades of research,
GC still seems to get in the way of performance, especially
for parallel programs.







Wouldn't it be great if the heap wasn't just some messy pile? What if we
could partition it into independent components?

Of course, we could arbitrarily partition it.

{% comment %}
Draw picture of messy heap of garbage. Grab a big scoop, but there's all
sorts of ropes and strings dangling into the original pile. We could try
to untangle it, but the best we can do is follow one rope at a time. Lots
of clashing hands... contention.

Can try this analogy:
  * pile of ropes
  * each rope is an object
  * rope x tied onto rope y means "x points to y"
  * a few of the ropes are attached to YOU (the roots)
{% endcomment %}


How can you partition
a seemingly unstructured memory graph into independent components? You could
do all sorts of graph analysis, e.g. to
