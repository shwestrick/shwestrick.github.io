---
layout: post
title: "Purely Functional Parallel Flattening"
mathjax: true
---

A curiosity grabbed ahold of me a couple weeks ago. The question is: how many
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
pairwise concatenation, sorting, and many others, all with good
theoretical performance (work-efficiency and polylog span) while still
remaining purely functional. Some examples are shown below.

{% highlight sml %}
fun reverse(A) =
  tabulate(length(A), fn i => A[length(A) - 1 - i])

fun zip(A, B) =
  tabulate(min(length(A), length(B)), fn i => (A[i], B[i]))

fun concatenate(A, B) =
  let
    val n = length(A)
    val m = length(B)
  in
    tabulate(n + m, fn i => if i < n then A[i] else B[i-n])
  end
{% endhighlight %}

Can we implement _everything_ with just `tabulate`? Answering that question
would take quite some time, and certainly more than one blog post. Today,
let's try making some progress by investigating one fundamental
operation: `flatten`, which concatenates many arrays together
in parallel. For example, `flatten [[1,2,3],[4],[],[5,6]]` should output
`[1,2,3,4,5,6]`. Our goal is to make something work-efficient
(linear work, in this case) and highly parallel (polylog span),
using just purely functional code with `tabulate`.

<img width="80%" src="/assets/functional-flatten/flatten.svg">

### Things that don't work (too slow)

**Reduce-concatenate**. One idea would be to do a parallel reduction with
pairwise concatenation: divide the input in half, recursively flatten the two
halves in parallel, and then concatenate the results. This approach is nicely
parallel, with polylog span. But even for a simple
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
    (** prefix sums of lengths ==> offset for each array
      * scan returns array of length +1, including total sum at end
      *)
    val offsets = scan(add, map(length, A))
    val num_elems = offsets[length(A)]

    (** Function to retrieve the ith output element.
      * Uses binary search to count number of arrays that
      * begin at or before index i.
      *)
    fun get_elem(i) =
      let
        val nleq = BinarySearch.count_less_or_eq(offsets, i)
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
$$O(\log n)$$ time, resulting again in $$O(n \log n)$$ total.

## The more you share, the more your bowl will be plentiful

Essentially, the binary-search approach (described above) does too much
redundant work. Each individual search adamantly goes
it alone, to the detriment of both itself and its peers. To do less work
overall, we need to convince some of the searches to share a little.

Here's a nice observation: if the $$i$$th output element resides
in the $$j$$th array, then any later element (at $$i' > i$$) must reside in
either the same array or a later one ($$j' \geq j$$). In other words, the
result of one search can be used as a lower bound for another search.
The same idea works for upper bounding searches, too.

It can be helpful to think of each search as splitting a range of indices in
half. By sharing upper- and lower-bounds, the amount of time it takes to do a
search is logarithmic in the width of the range it splits. So, by beginning with
just a few searches and then increasing the number of searches exponentially, we
can quickly split the entire space, as shown below.

<img width="80%" src="/assets/functional-flatten/sharing-searches.svg">

Each round is just a `tabulate` to compute a bunch of binary searches.
On round $$i$$, we perform $$2^i$$ searches, each costing $$\log \frac n {2^i}$$.
At $$i = \log n$$, we are done (because then we know for each element how
many subarrays precede it). The total work is approximately
$$\sum_{i=0}^{\log n} 2^i \log \frac n {2^i}$$ which is $$O(n)$$. The total
span is polylogarithmic, as there are only $$\log n$$ rounds, and each round
requires logarithmic span.

Admittedly, we're being a little sloppy here with asymptotics. A proper analysis
needs to discuss two quantities simultaneously: the total number of
elements $$n$$, and the number of subarrays $$m$$. For example, for
`flatten [[1,2,3],[4],[],[5,6]]`, there are $$n=6$$ elements and $$m=4$$
subarrays.

Note though that as long as each subarray has at least one element,
the analysis above still works. In the more general case (where there are lots
of empty subarrays), we need to additionally guarantee that each round cuts
the number of subarrays in each range in half. This can be done by
performing two binary searches at each split instead of one. The two searches
will compute (1) the number of subarrays beginning at or before some index, and
(2) the number of subarrays that begin strictly before the same index. By using
the results of (1) as lower bounds and the results of (2) as upper bounds, we
achieve $$O(n + m)$$ work, still with polylog span.

## Where does that leave us?

In this post I showed that `flatten` is implementable in terms of `tabulate`
using only purely functional code, with theoretically good asymptotic performance.
In practice however, we are going to need a few more tweaks to make the
algorithm fast. Perhaps I'll cover that in another post.

The really fun thing about purely functional parallel algorithms is the
miniscule gap between design and implementation. The full algorithm is only
about 50 lines of Standard ML, and most of that code I wrote during the
design process. To understand the algorithm, we don't even
need to know that it's parallel; we can just imagine the algorithm running
sequentially, and know that it will also be correct in parallel. In comparison
to juggling concurrency footguns... what a breeze.
