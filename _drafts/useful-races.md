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
help eliminate a bottleneck caused by unnecessary synchronization and/or memory
traffic.

Now, first, let me emphasize: **I'm not talking about data races**.
Data races are typically bugs, by definition.[^1]
Instead, I'm talking about how to utilize atomic in-place updates and accesses
(e.g., compare-and-swap, fetch-and-add, etc.) to trade a small amount of
non-determinism for improved performance.

Two interesting examples are
[priority updates](https://www.cs.cmu.edu/~blelloch/papers/SBFG13.pdf) and
[deterministic reservations](https://www.cs.cmu.edu/~jshun/determ.pdf).
Both techniques are able to ensure some degree of determinism, and
yet are non-deterministic "under the hood". In this post, we'll look at
priority updates.

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

<!--## Starting Point: Parallel, but not Concurrent-->

<!--It's helpful for this discussion to distinguish parallelism from concurrency.-->

<!--In the world of **concurrent programming**, there are situations where race
conditions are fundamental and unavoidable. For example, if you are developing
an interactive website, then you don't know when a user might press a button.
What happens if the button is pressed before the page finishes loading? That's
a race condition you might have to consider.-->

<!--In contrast, in the world of **parallel programming**, race conditions are
optional. It's possible to write parallel programs which are race-free.
Such programs are entirely deterministic,[^2] making it possible to ignore
parallelism when reasoning about correctness.
"Purely functional" programs are a classic example of this: by
disallowing in-place updates, it's possible to avoid all race conditions by
default.-->

<!--Our starting point here is **race-free parallel programming**, where
correctness does not depend on any race conditions. We'll then show how to
improve performance by introducing races.-->

## Parallel Breadth-First Search (BFS)

Our running example is a parallel breadth-first search. This algorithm operates
in a series of rounds, where on each round it visits a ***frontier*** of vertices
which are all the same distance from the ***source*** (the initial vertex). By
selecting the subset of edges which are "used" to traverse the graph, we
derive a ***BFS tree***. In the BFS tree, each vertex points to its
***parent***, which is a vertex from the previous frontier.

For example, here are an example graph with vertices labeled 0 through 9,
and one possible BFS tree, with frontiers highlighted, starting with vertex 0
as a the source. In this graph, the maximum distance from the source is 3,
so there are 4 frontiers (corresponding to distances 0, 1, 2, and 3).

<table class="images">
<tr>
  <td><img src="/assets/racy/graph.png">input graph</td>
  <td><img src="/assets/racy/tree-and-frontiers.png">BFS tree (bold edges) and frontiers (highlighted regions)</td>
</tr>
</table>

## Selecting Parents in Parallel

On each round of BFS, we have a frontier of
vertices, and we need to compute the next frontier. To do so, we need to select
a parent for each vertex.

Selecting a parent for each vertex requires care, because for each vertex, there
might be multiple possible parents. For example, in the images above, vertex 3
is used as the parent of vertex 4, but both vertices 1 and 2 are valid options
as well.

**Slow approach: collect potential parents and then deduplicate**.
One reasonable approach is to first compute the set of potential
parents, and then select parents from these. The set of
potential parents is a list of pairs $$(v,u)$$ where $$u$$ is a potential
parent of $$v$$, and we can select parents by "deduplicating": for any
two pairs $$(v, u_1)$$ and $$(v, u_2)$$, we keep one and remove the other
(and continue until there are no duplicates).

One nice thing about this approach is that it is easy to make deterministic.
Deduplication can (for example) be implemented by first
[semisorting](https://people.csail.mit.edu/jshun/semisort.pdf) to put
duplicate pairs in the same bucket, and then by selecting one element from each
bucket. This results in deterministic parent selection in linear work and
polylog depth.

However, one not-so-nice thing about this approach is that **it is slow**,
because it has to construct the set of potential parents. Across the whole BFS, every
edge will be considered as a potential parent once. Therefore, constructing the
set of potential parents incurs a total of approximately $$2|E|$$ writes to
memory for $$|E|$$ edges in the input graph. (The factor of 2 is due to
representing potential parents as a list of pairs.)

That's a lot of memory traffic which could be avoided.

**Faster approach: deduplicate "on-the-fly" with priority updates.**


<!--{% highlight sml %}
(* parents[v] is the parent of v, or -1 if not yet visited *)
val parents: vertex array = ...
fun unvisitedNeighbors(u) =
  filter(neighbors(u), fn v => parents[v] == -1)
val currentFrontier: vertex array = ...
(* potentialParents = all pairs (v,u) such that
 *   v will be in the next frontier, and
 *   u is in current frontier.
 *)
val potentialParents: (vertex * vertex) array =
  flatten(map(currentFrontier, fn u =>
    map(unvisitedNeighbors(u), fn v => (v, u))))
(* Eliminate "duplicates" of the form (v, u1) and (v, u2).
 * This effectively selects a parent for each vertex.
 * Implementation of `deduplicate` omitted.
 *)
val treeEdges: (vertex * vertex) array =
  deduplicate(potentialParents)
(* Now visit vertices by marking their parents *)
val _ = foreach(treeEdges, fn (v,u) => parents[v] := u)
(* Finally, construct next frontier *)
val nextFrontier = map(treeEdges, fn (v, u) => v)
{% endhighlight %}-->

## An Implementation in Parallel ML

<!-- val tabulate: int * (int -> 'a) -> 'a array
val map: 'a array * ('a -> 'b) -> 'b array
val filter: 'a array * ('a -> bool) -> 'a array
val flatten: 'a array array -> 'a array
val dedupVertices: vertex array -> vertex array -->

Here's a simple function for a parallel breadth-first search, written
in a mostly functional style, using standard data-parallel functions like
`map`, `filter`, `flatten`, etc., as well as a few in-place updates.
(This is similar to the code we could write for
[`mpl`](https://github.com/MPLLang/mpl)).

The function `breadthFirstSearch(G,s)` performs a
breadth-first search of graph `G`, starting from a vertex `s`.
We assume vertices are integers, labeled `0` to `N-1`. The search returns an
array of parents, with one parent for each vertex. In the array of parents, a
value of `-1` is used to mark unvisited vertices (i.e., vertices without a
parent). This way, the array of parents serves two purposes: it will be the
output, but also, it is used to indicate which vertices have been visited.

BFS begins by allocating the array of parents, initializing with `-1` for
each vertex, indicating that no vertices have been visited yet. The BFS then
proceeds in a series of rounds, where each round takes as argument the
*frontier* of the previous round. We then compute the next frontier by
selecting parents as described above.

The BFS terminates as soon as the current frontier is empty, which occurs as
soon as all vertices reachable from the source have been visited.

{% highlight sml %}
fun breadthFirstSearch(G: graph, source: vertex) : vertex array =
  let
    val parents: bool array = tabulate(numVertices(G), fn v => -1)

    (* Try to visit v from potential parent u. Returns `true` if
     * this is the first time the parent of v has been updated.
     * After all priority updates have completed, the parent of v
     * will be the maximum of all potential parents.
     *)
    fun priorityUpdate(v,u) =
      let
        val old = parents[v]
        val isFirstVisit = old == -1
      in
        if u <= old then
          false (* v previously visited with a larger parent *)
        else if compareAndSwap(parents, v, old, u) then
          isFirstVisit
        else
          priorityUpdate(v,u) (* retry: CAS contention *)
      end

    fun tryVisitNbrs(u) =
      filter(neighbors(G,u), fn v => tryVisit(v,u))

    (* One round of BFS. The frontier is the set of vertices
     * visited on the previous round. *)
    fun computeNextFrontier(frontier: vertex array) : vertex array =
      flatten(map(frontier, tryVisitNbrs))

    fun bfsLoop(frontier: vertex array) =
      if size(frontier) = 0 then () (* done *)
      else bfsLoop(computeNextFrontier(frontier))

    val firstFrontier = singletonArray(s)
  in
    parents[s] := s;        (* visit source (use self as parent) *)
    bfsLoop(firstFrontier); (* do the search *)
    parents                 (* return array of parents *)
  end
{% endhighlight %}

-------------

-------------

[^1]: In the context of a language memory model, a *data race* is typically defined as two conflicting concurrent accesses which are not "properly synchronized" (e.g., non-atomic loads and stores, which the language semantics may allow to be reordered, optimized away, etc). Data races can lead to incorrect behavior due to miscompilation or lack of atomicity, and are therefore often considered undefined behavior. In other words, in many languages, data races are essentially bugs by definition. One recent exception is the OCaml memory model, which is capable of providing a reasonable semantics to programs with data races. See [Bounding Data Races in Space and Time](https://kcsrk.info/papers/pldi18-memory.pdf), by Stephen Dolan, KC Sivaramakrishnan, and Anil Madhavapeddy.

[^2]: Assuming no other sources of non-determinism, such as true randomness.
