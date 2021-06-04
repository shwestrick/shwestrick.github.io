---
layout: post
title: "Purely Functional Parallel Flattening"
mathjax: true
---

A curiosity grabbed ahold of me a couple weeks ago. The question is: what
primitives do we really need in a general purpose, parallel, functional
programming language? After all, many interesting functions can be expressed
in terms of one another. Perhaps the simplest example would be implementing
a parallel `map` on arrays in terms of `tabulate`, i.e. the "build-an-array"
function, which in parallel applies a function for
each index and produces a fresh array.

{% highlight sml %}
(** outputs [ f(A[0]), f(A[1]), ... ] *)
fun map(f, A) = tabulate(length(A), fn i => f(A[i]))
{% endhighlight %}

The `tabulate` primitive turns out to be surprisingly general. From it, we
can implement parallel prefix sums, parallel reduction, reverse, zipping,
pairwise concatenation, parallel sorting, and many others, all with good
theoretical performance (work-efficiency and polylog span) while still
remaining purely functional.

Can we implement _everything_ with just `tabulate`? Let's see! Let's try
to implement another fundamental operation,
`flatten: 'a array array -> 'a array`, which concatenates many arrays
together. For example, `flatten [[1,2,3],[4],[],[5,6]]` produces
`[1,2,3,4,5,6]`. Our goal is to make something work-efficient
(linear work, in this case) and highly parallel (polylog span),
using just purely functional code with `tabulate`.

## Things That Don't Work (Too Slow)

**Reduce-concatenate**. One idea would be to do a parallel reduction with
pairwise concatenation: divide the input in half, recursively flatten the two
halves in parallel, and then concatenate the results. (Concatenating is just
a single call to `tabulate`.) This approach is nicely parallel, as it has
polylog span. But even for a simple
case, say $$n$$ arrays each of length $$1$$, the total amount of work is too
much. Concatenating two arrays takes linear work, so the whole computation would
take $$W(n) = 2 W(n/2) + O(n)$$, which comes out to $$O(n \log n)$$. No good!
Our goal is $$O(n)$$.

**Pull by searching offsets**. Another nice idea is to first compute the
offset of each subarray, and then pull each element into the output by binary
searching on the offsets. Computing the offsets can be done with `scan`
(parallel prefix sums) which in turn can be implemented entirely in terms of
`tabulate` in linear work and polylog span (perhaps this will be another post
in the future). The code is shown below, as it's quite nice.

{% highlight sml %}
fun slow_flatten(A) =
  let
    (** prefix sums of lengths ==> offset for each array *)
    val offsets = scan(op+, map(length, A))
    val num_elems = offsets[length(A)]

    (** Function to retrieve the ith output element.
      * Uses binary search to count number of arrays that
      * begin at or before index i.
      *)
    fun get_elem(i) =
      let
        val nleq = BinarySearch.num_less_or_eq(offsets, i)
        val outer_idx = nleq - 1
        val inner_idx = i - offsets[outer_idx]
      in
        A[outer_idx][inner_idx]
      end
  in
    tabulate(num_elems, get_elem)
  end
{% endhighlight %}

Unfortunately however, this also does too much work! Each binary search takes
$$O(\log n)$$ time, resulting again in $$O(n \log n)$$ total. Essentially, the
problem with this approach is that it does too much redundant work. But we
can adapt this approach to get a faster solution by convincing the binary
searches to share a little.

## Share To Save Time

Let's run with the binary-searching idea described above. To make it faster,
here's a nice observation: if the $$i$$th output element resides
in the $$j$$th array, then any later element (at $$i' > i$$) must reside in
either the same array or a later one ($$j' \geq j$$). In other words, the
result of one search can be used as a lower bound for another search (and
similarly for upper bounds).


