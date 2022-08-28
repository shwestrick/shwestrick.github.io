---
layout: post
title:  "Race Conditions Can Be Useful for Parallelism"
mathjax: true
---

Programmers are well aware of the hazards of race conditions. But what about
the benefits?

There are situations where race conditions can be helpful for
performance. By this, I mean that
**you can sometimes make a program faster by *creating* race conditions**.
Essentially, a small amount of non-determinism can
help eliminate a synchronization bottleneck.

Now, first, let me emphasize: **I'm not talking about data races**.
Data races are typically bugs, by definition.[^1]
Instead, I'm talking about how to utilize atomic in-place updates and accesses
(e.g., compare-and-swap, fetch-and-add, etc.) to trade a small amount of
non-determinism for improved performance.

We'll look at two techniques in particular, from two papers by
Julian Shun, Guy Blelloch, Jeremy Fineman, and Phil Gibbons:
[priority updates](https://www.cs.cmu.edu/~blelloch/papers/SBFG13.pdf), and
[deterministic reservations](https://www.cs.cmu.edu/~jshun/determ.pdf).
Both techniques are able to ensure some degree of determinism, and
yet are non-deterministic "under the hood".

It's important for parallel programmers to be aware of these
techniques for a couple reasons. First, the performance advantages
(for both space and time) are significant. But perhaps more importantly,
these techniques demonstrate that race conditions can be disciplined,
easy to reason about, and useful.

<!-- Familiarizing yourself with this area of algorithm design
forces you to do away with any fears you might have about race conditions.
At a certain point, something clicks, and suddenly, race conditions become
just another thing that you are comfortable reasoning about when trying to
convince yourself that the code you wrote is correct. -->

<!-- If you have ever attempted to design a lock-free or wait-free concurrent
data structure, you are likely aware that there is a whole world of
programming where programmers embrace, rather than eschew, race conditions.
I believe every programmer should at least
become familiar with this area of algorithm and data-structure design. It's
valuable because it forces you to do away with any fears you might have
about race conditions. At a certain point, something clicks, and suddenly,
race conditions become just another thing that you are comfortable reasoning
about when trying to convince yourself that the code you wrote is correct. -->

## Starting Point: Parallel, but not Concurrent

It's helpful for this discussion to distinguish parallelism from concurrency.

In the world of **concurrent programming**, there are situations where race
conditions are fundamental and unavoidable. For example, if you are developing
an interactive website, then you don't know when a user might press a button.
What happens if the button is pressed before the page finishes loading? That's
a race condition you might have to consider.

In contrast, in the world of **parallel programming**, race conditions are
optional. It's possible to write parallel programs which are race-free.
Such programs are entirely deterministic,[^2] making it possible to ignore
parallelism when reasoning about correctness.
"Purely functional" programs are a classic example of this: by
disallowing in-place updates, it's possible to avoid all race conditions by
default.

Our starting point here is **race-free parallel programming**, where
correctness does not depend on any race conditions. We'll then show how to
improve performance by introducing races.

## Race-Free BFS (Breadth-First Search)

<!-- val tabulate: int * (int -> 'a) -> 'a array
val map: 'a array * ('a -> 'b) -> 'b array
val filter: 'a array * ('a -> bool) -> 'a array
val flatten: 'a array array -> 'a array
val dedupVertices: vertex array -> vertex array -->

Here's a simple function for a parallel breadth-first search, written
in a mostly functional style, using standard data-parallel functions like
`map`, `filter`, `flatten`, etc., as well as a few in-place updates.
(This is similar to the code we could write for
[`mpl`](https://github.com/MPLLang/mpl)). As written, the code is entirely
race-free: it never loads and stores at the same memory location concurrently.

{% highlight sml %}
(* remove duplicate vertices; implementation omitted *)
fun deduplicate(vertices: vertex array) : vertex array = ...

fun breadthFirstSearch(G: graph, source: vertex) : bool array =
  let
    (* one "visited" flag for each vertex, all initially false *)
    val flags: bool array =
      tabulate(numVertices(G), fn v => false)

    fun getUnvisitedNbrs(u) =
      filter(neighbors(G,u), fn v => not(flags[v]))

    (* One round of BFS. The frontier is the set of vertices
     * visited on the previous round. *)
    fun computeNextFrontier(frontier: vertex array) : vertex array =
      let
        (* Step 1: find all unvisited neighbors *)
        val nbrs = flatten(map(frontier, getUnvisitedNbrs))
        (* Step 2: remove duplicates *)
        val nextFrontier = deduplicate(nbrs)
      in
        (* Step 3: visit every vertex in the new frontier *)
        foreach(nextFrontier, fn v =>
          flags[v] := true
        );
        nextFrontier (* return new frontier *)
      end

    fun bfsLoop(frontier: vertex array) =
      if size(frontier) = 0 then () (* done *)
      else bfsLoop(computeNextFrontier(frontier))

    val firstFrontier = singletonArray(source)
  in
    flags[source] := true;  (* visit source *)
    loop(firstFrontier);    (* do the search *)
    flags                   (* return visited flags *)
  end
{% endhighlight %}


The function `breadthFirstSearch(G,source)` performs a
breadth-first search of graph `G`, starting from a vertex `source`.
We assume vertices are integers, labeled `0` to `N-1`. The search returns an
array of booleans, with one bool for each vertex, indicating whether or not
the vertex is reachable from the `source` vertex.

BFS begins by allocating a collection of "visited" flags, one for each vertex,
which indicate whether or not each vertex has been visited. It then
proceeds in a series of rounds, where each round takes as argument a list
of vertices that were visited on the previous round, called the *frontier*.
One round computes the next frontier by performing three bulk actions, each of
which is parallelized:
  1. first, find all unvisited neighbors of the current frontier;
  2. second, remove duplicates (producing the next frontier); and
  3. finally, "visit" vertices in the next frontier, by setting their flags.

The BFS terminates as soon as the current frontier is empty, which occurs as
soon as all vertices reachable from the source have been visited.

## Utilizing Races to Make BFS Faster



-------------

-------------

[^1]: In the context of a language memory model, a *data race* is typically defined as two conflicting concurrent accesses which are not "properly synchronized" (e.g., non-atomic loads and stores, which the language semantics may allow to be reordered, optimized away, etc). Data races can lead to incorrect behavior due to miscompilation or lack of atomicity, and are therefore often considered undefined behavior. In other words, in many languages, data races are essentially bugs by definition. One recent exception is the OCaml memory model, which is capable of providing partial semantics to programs with data races. See [Bounding Data Races in Space and Time](https://kcsrk.info/papers/pldi18-memory.pdf), by Stephen Dolan, KC Sivaramakrishnan, and Anil Madhavapeddy.

[^2]: Assuming no other sources of non-determinism, such as true randomness.
