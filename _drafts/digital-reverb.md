---
layout: post
title:  "Parallel Digital Reverb, Or: How I Optimized the Heck Out of a Comb Filter"
mathjax: true
comments: true
---

While browsing through
[The Computer Music Tutorial](https://mitpress.mit.edu/books/computer-music-tutorial)
by
[Curtis Roads](https://en.wikipedia.org/wiki/Curtis_Roads),
I came across a beautifully simple *reverberator* circuit. This circuit
simulates the acoustic effect of a particular space---such as a concert
hall or cathedral---using only two components:
[***comb***](https://en.wikipedia.org/wiki/Comb_filter) and
[***all-pass***](https://en.wikipedia.org/wiki/All-pass_filter) filters.
The filters can be tuned to simulate a variety of different spaces.

<img width="80%" src="/assets/reverb/design.svg">

<div class="remark">
This design is fairly old; it's credited to
[Manfred Schroeder](https://en.wikipedia.org/wiki/Manfred_R._Schroeder)
during his time at [Bell Labs](https://en.wikipedia.org/wiki/Bell_Labs)
in the mid 20<sup>th</sup> centure.
From what I can tell, nowadays people are mostly using alternative
techniques such as
[convolution reverb](https://en.wikipedia.org/wiki/Convolution_reverb).
</div>

My first thought was how fun it would be to turn this circuit
into a parallel benchmark for
[`mpl`](https://github.com/mpllang/mpl), the compiler I'm developing at
Carnegie Mellon University. And soon enough, I found myself deep in the rabbit
hole of writing code and running experiments.

Here are the results. Impressive, for a circuit so simple!

<table class="images">
<tr>
  <td class="shrink ralign">original</td>
  <td>
    <audio controls>
      <source src="/assets/reverb/priorities.mp3" type="audio/mp3">
      Your browser does not support audio playback.
    </audio>
  </td>
</tr>

<tr>
  <td class="shrink ralign">with reverb</td>
  <td>
    <audio controls>
      <source src="/assets/reverb/priorities-rev.mp3" type="audio/mp3">
      Your browser does not support audio playback.
    </audio>
  </td>
</tr>
</table>

**In this post, I describe the process of designing and implementing a fast
parallel reverb algorithm**, based on the circuit shown above.
At first, seeing as how the circuit is built
from two components (comb and all-pass filters), it might seem that we need to
design two algorithms.
But it turns out that if you have a fast comb filter, then you essentially
[already have a fast all-pass algorithm](#all-pass-with-comb), for free.
**So, most of my effort** went into
[designing and implementing a fast comb filter](#par-comb-section)
and optimizing it to
[reduce the number of writes](#fewer-memory-writes)
and
[increase the number of cache hits](#cache-hits).
Overall, this turned out to be much more interesting (and trickier) than I
expected. **After powering through a fiery hell of off-by-one index arithmetic**,
I [managed to get the overhead down](#performance)
to approximately $$2\times$$ and [speedups](#speedup-plot) up to $$11\times$$.
The self-scalability is quite impressive: up to $$27\times$$.

If you have any comments, [leave a note below](#respond)!
And if you're curious to see source code, check out
[my initial work](https://github.com/MPLLang/mpl/pull/122)
and
[final implementation](https://github.com/MPLLang/mpl/commit/7fee9cdfce3fe56596ba93e25159b17aeef9e090)
on GitHub.

## What is a Comb Filter?
{: #comb-filter}

A [feedback comb filter](https://en.wikipedia.org/wiki/Comb_filter#Feedback_form)
produces many equally-spaced echoes of a sound, where each echo is
dimished in intensity. I've drawn an example below. The input
appears first, colored in blue, and each distinct echo is a different color.
(The actual output signal would be the sum of all
these echoes together as one signal.)

<img src="/assets/reverb/comb-signal.svg">

Essentially, a comb filter combines two effects: attenuation and delay.

<table class="images">
<tr>
  <td><img src="/assets/reverb/attenuate.svg">Attenuation</td>
  <td><img src="/assets/reverb/delay.svg">Delay</td>
</tr>
</table>

If a large enough delay between echoes is used, the effect of a comb filter
is essentially the same as the looping "delay" effect which is sometimes
used by musicians (particularly electric guitarists, for example with
an
[effect pedal](https://en.wikipedia.org/wiki/Delay_(audio_effect)#Digital_delay)).
But when the delay is small---say, on the order
of milliseconds---the effect of a comb filter is primarily "spectral", causing
us to perceive it as modifying the
[quality of the sound](https://en.wikipedia.org/wiki/Timbre) itself.

<table class="images">
<tr>
  <td class="shrink ralign">original</td>
  <td>
    <audio controls>
      <source src="/assets/reverb/priorities.mp3" type="audio/mp3">
      Your browser does not support audio playback.
    </audio>
  </td>
</tr>

<tr>
  <td class="shrink ralign">half-second comb</td>
  <td>
    <audio controls>
      <source src="/assets/reverb/priorities-5.mp3" type="audio/mp3">
      Your browser does not support audio playback.
    </audio>
  </td>
</tr>

<tr>
  <td class="shrink ralign">10 millisecond comb</td>
  <td>
    <audio controls>
      <source src="/assets/reverb/priorities-01.mp3" type="audio/mp3">
      Your browser does not support audio playback.
    </audio>
  </td>
</tr>
</table>

<div class="remark">
The name "comb filter" comes from the effect that the comb filter has
in the [frequency domain](https://en.wikipedia.org/wiki/Frequency_domain):
it results in equally spaced peaks, like the tines of a comb.
</div>

Working with analog circuitry, a comb filter can be implemented with
a simple feedback loop, as shown below. Each time around
the loop, the signal is delayed and attenuated (scaled by some $$\alpha \in
[0,1]$$).

<img width="65%" src="/assets/reverb/comb.svg">

**Comb Filter Equation**.
Mathematically, a comb filter can be defined by the following equation.
We write $$S[i]$$ for the $$i$$<sup>th</sup> sample of the input,
and similarly $$C[i]$$ for a sample of the output. The constant $$D$$ is
the delay (measured in samples) between echoes, and
$$\alpha \in [0,1]$$ controls the intensity of each successive echo.
{: #comb-equation}

$$
C[i] = S[i] + \alpha C[i - D]
$$

## All-Pass Filters Are Fancy Combs
{: #all-pass-with-comb}

An [all-pass filter](https://en.wikipedia.org/wiki/All-pass_filter)
affects the
[phase](https://en.wikipedia.org/wiki/Phase_(waves)) of different frequencies,
shifting them around, causing the original sound to become "mis-aligned".
This is commonly used in electronic music to implement an effect
called a [phaser](https://en.wikipedia.org/wiki/Phaser_(effect)).
The name "all-pass" comes from the fact that all frequencies of the input
are allowed to "pass through", unmodified in strength.

A typical analog implementation of an all-pass circuit might look like this:

<img width="75%" src="/assets/reverb/allpass.svg">

Looking closely, notice that the all-pass circuit uses a feedback loop
which looks a lot like a comb filter. If
we rearrange some things, we can see that an all-pass filter is actually
just a comb filter with some extra machinery.

<img width="75%" src="/assets/reverb/allpass-with-comb.svg">

Mathematically, the following equation is another way of saying the same
thing. ($$S$$ is the input signal, $$C$$ is the result of combing the input, and
$$A$$ is the output of the all-pass.)

$$
A[i] = -\alpha S[i] + (1-\alpha^2) C[i-D]
$$

This is good news, because now we can focus on just implementing the comb
filter. Once we have it, we get an all-pass filter essentially for free.

## Parallel Comb Filter
{: #par-comb-section}

At a high level, the comb filter problem is to solve the
[comb filter equation](#comb-equation) $$C[i] = S[i] + \alpha C[i - D]$$,
where the inputs are $$S$$, $$\alpha$$, and $$D$$, and the output is $$C$$.

The parallel algorithm I came up with is based on two ideas.
  1. First, we can [split the problem into independent "columns"](#par-columns-comb).
  These columns can computed in parallel, however this
  does not expose enough parallelism on its own, especially for small values of
  $$D$$ (the delay parameter).
  2. Next, we can [parallelize each column](#geometric-prefix-sums). To do
  so, I identify a problem called ***geometric prefix-sums***. Each column is
  one instance of the geometric prefix-sums problem, and we can solve it
  by adapting a well-known algorithm for
  [parallel prefix-sums](https://en.wikipedia.org/wiki/Prefix_sum#Parallel_algorithms).

Combining the two ideas above, we get an algorithm for computing
the comb filter with $$O(N)$$ work and $$O(\log(N/D))$$ span, which is
work-efficient (asymptotically, it performs the same amount of work as the
fastest possible sequential algorithm) and highly parallel.

<div class="algorithm" name="(Parallel Comb Filter)">
[Split the input into columns](#par-columns-comb) and then in parallel compute
the [geometric prefix-sums](#geometric-prefix-sums) of the columns.
</div>
{: #parallel-comb-alg}

<div class="remark">
[Work and span](https://en.wikipedia.org/wiki/Analysis_of_parallel_algorithms)
are abstract cost measures of a parallel algorithm. The ***work*** is the
total number of operations performed, and the ***span*** is the number of
operations on the critical path (i.e. the longest chain of operations that
must occur sequentially one-by-one).

Given an algorithm with work $$W$$ and span $$S$$, a computer with $$P$$
processors can execute that algorithm in $$O(W/P + S)$$ time. Intuitively,
on each step the computer executes up to $$P$$ operations (one on each
processor), but there must be at least $$S$$ steps overall.
</div>

# Splitting Into Columns
{: #par-columns-comb}

The
[comb filter equation](#comb-equation) $$C[i] = S[i] + \alpha C[i - D]$$
can be broken up into $$D$$ independent computations.
Specifically, imagine laying out $$C$$ as a
matrix, where at row $$i$$ and column $$j$$ we put $$C[iD + j]$$.
In this layout, each column is a standalone computation, completely independent
of the values in the other columns. For example, as soon as we know the value
$$C[2]$$, we can immediately compute $$C[D+2]$$ and then $$C[2D+2]$$, etc.

<img width="60%" src="/assets/reverb/comb-columns.svg">

Since the columns are independent of one another, we can compute them in
parallel. But what do we do inside each column? We could proceed sequentially
from top to bottom... however, this does not provide
enough parallelism. One column
contains up to $$\lceil N / D \rceil$$ elements, leaving us
with $$O(N/D)$$ span, which for small values of $$D$$ is not very parallel
at all. Ideally, we'd like to be able to do a single column in logarithmic
span, say $$O(\log(N/D))$$.

# Parallelizing Each Column
{: #geometric-prefix-sums }

In this section, I show how each column is essentially a variant of the
[prefix-sums problem](https://en.wikipedia.org/wiki/Prefix_sum#Parallel_algorithms)
and describe how to adapt a well-known algorithm.

**Setting the Stage**.
The $$i$$<sup>th</sup> input of the $$j^\text{th}$$ column is $$S[iD+j]$$,
and similarly the outputs are $$C[iD+j]$$. Let's simplify the dicussion by defining
$$X[i] = S[iD+j]$$ and taking $$X$$ as our input sequence.
Then, abstractly, the problem we're trying to solve is to produce a sequence
$$Y$$ where $$Y[i] = C[iD+j]$$, i.e. the output column of combed samples.

With this setup, the [comb filter equation](#comb-equation) gives us the
following recurrence for $$Y$$.

$$
Y[i] = X[i] + \alpha Y[i-1]
$$

If we unroll this recurrence, we can see that each output element is a
prefix-sum of inputs scaled by powers of $$\alpha$$.

$$
Y[i] = \sum_{k=0}^i \alpha^{i-k} X[k]
$$

Let's call this problem the ***geometric prefix-sums problem***. We
can solve it with following algorithm, which I've adapted from a
[parallel prefix-sums algorithm](https://en.wikipedia.org/wiki/Prefix_sum#Parallel_algorithms).

<div class="algorithm" id="alg-geometric-prefix-sums" name="(Parallel Geometric Prefix-Sums)">

**Inputs**: $$\alpha \in [0,1]$$ and sequence $$X$$.

**Output**: sequence $$Y$$ where $$Y[i] = \sum_{k=0}^i \alpha^{i-k} X[k]$$.

The algorithm consists of three steps:
1. (Contraction Step) In parallel, combine adjacent input elements in "blocks"
of size 2. Specifically, for each even $$i$$, compute $$\alpha X[i] + X[i+1]$$.
These are called the ***block-sums***. Note that there are half as many
block-sums as input values, so we've reduced the problem in half.
2. (Recursive Step) Recursively compute the geometric prefix-sums of the block-sums.
In the recursive call, use $$\alpha^2$$ instead of $$\alpha$$.
The results of this step are the *odd indices of* $$Y$$.
3. (Expansion Step) Fill in the missing (even) indices by computing
$$Y[i] = X[i] + \alpha Y[i-1]$$ for each even $$i$$. Note that each $$Y[i-1]$$
is one of the outputs of the previous step.
</div>

Here's an example for an input of size 6.

<img width="80%" src="/assets/reverb/prefix-sums-contraction.svg">

Note that the results of the recursive call are *geometric prefix-sums of
block-sums*. For example, $$Y[3]$$ is the geometric prefix-sum
(using $$\alpha^2$$) of two block-sums:

<img width="55%" src="/assets/reverb/y3-breakdown.svg">

<!-- **Granularity Control**.
This algorithm works for any block-size,
giving us an opportunity for
[granularity control](https://en.wikipedia.org/wiki/Granularity_%28parallel_computing%29).
For a block-size $$B$$, we need to use a scaling factor of
$$\alpha^B$$ in the recursive step (instead of $$\alpha^2$$ as originally
described). Producing
the missing indices in the "expansion" step is also slightly more involved: the
first value within each output block is the same as before, but then we need
to continue scanning through the block to fill in the other nearby missing
indices. -->

**Work and Span**.
On an input of size $$N$$, the geometric prefix-sums algorithm
recursively uses a problem of size $$N/2$$ and otherwise does $$O(N)$$ work,
all of which is fully parallel. This yields the following work and span
recurrences, which solve to $$O(N)$$ work and $$O(\log N)$$ span.
* Work: $$W(N) = W(N/2) + O(N)$$
* Span: $$S(N) = S(N/2) + O(1)$$

Applying the geometric prefix-sums algorithm to a column of
size $$\lceil N/D \rceil$$, we have an algorithm for computing one column of
the comb filter in $$O(N/D)$$ work and $$O(\log(N/D))$$ span. In total,
for $$D$$ columns, that gives us a parallel comb algorithm with
$$O(N)$$ work and $$O(\log(N/D))$$ span. Nice!

## Making It Fast In Practice

Our parallel comb algorithm is fast in theory: it is asymptotically
***work-efficient*** (it matches the work of the fastest
possible sequential algorithm) and ***highly parallel*** (it has low
span---logarithmic, in this case).

**But is the algorithm fast in practice?**
If implemented exactly as described above, no! I tried this, and found that
a naive implementation of our parallel comb algorithm is as much as
*12 times slower* on one processor than a fast sequential implementation.

<div class="remark">
It's easy to make the mistake of focusing on
*scalability*, not raw speed. That is, I could have told you that my naive
code gets 7.5 times faster when I use 8 processors instead of 1, and that
would have seemed pretty good. But still, it's slower than the
sequential code, so
[what's the point](http://www.frankmcsherry.org/assets/COST.pdf)?

My naive implementation is useless for machines with just a few processors.
And even with large multicores, it's still not very efficient to use an
*order of magnitude more energy* just to get
the same result in slightly less time.
</div>

<!--(The fast sequential comb
algorithm is extremely simple: just output $$C[i]$$ according to the
[comb filter equation](#comb-equation) in increasing order of $$i$$
looking up previously output values $$C[i-D]$$ as needed.)-->
<!--on an input of size
22MB (about 4 minutes of audio with 16-bit samples at a sample rate of 44.1kHz),
the parallel code takes about 0.45 seconds, but the fast sequential code takes
only 0.06 seconds. That's a difference of 8x!-->

**To make the algorithm fast**, we need to reduce the amount of work it
performs by nearly an order of magnitude. This might seem like a daunting
optimization task, but there are some really easy fixes we can make that will
get us most of the way there:
[reducing the number of writes](#fewer-memory-writes),
and
[increasing the number of cache hits](#cache-hits).

# Fewer Memory Writes
{: #fewer-memory-writes}

When designing parallel algorithms, it can be really helpful to consider
how many memory updates the algorithm performs. Simply put, updating memory is
expensive, but reading from memory is fast (and parallelizes well). If we
can reduce the overall number of writes to memory, then we might be able to
improve practical performance.

So let's count the number of memory updates performed by our
[parallel geometric prefix-sums algorithm](#geometric-prefix-sums) on an input
of size $$N$$, written $$u(N)$$. The algorithm first constructs an array of
$$N/2$$, then recurses on this array, and finally constructs an array of size
$$N$$. Adding these all up, we have $$u(N) = u(N/2) + 3N/2$$ which solves to
$$u(N) \approx 3N$$. That is, the algorithm performs about $$3N$$ memory
updates on an input of size $$N$$.

Now compare this against the fastest possible sequential geometric prefix-sums
algorithm. Sequentially, we can do exactly $$N$$ writes with a single
left-to-right pass over the input data. Our parallel algorithm does
**three times as many writes**! Perhaps this is a significant source of
overhead. Let's try to decrease it.

**Fewer Writes with Bigger Blocks**. Recall that the
[parallel geometric prefix-sums algorithm](#geometric-prefix-sums) begins by
computing $$N/2$$ "block-sums", where the blocks are size 2. We can generalize
this to any constant block-size $$B$$ as follows.
1. In the contraction step, scan through each block entirely to compute its
block-sum. For example with $$B=3$$, the block-sum of a block starting at
index $$i$$ would be $$\alpha^2 X[i] + \alpha X[i+1] + X[i+2]$$.
2. In the recursive step, use a scaling factor of $$\alpha^B$$. The results
of this step are the outputs at indices $$B-1$$, $$2B-1$$, etc.
3. In the expansion step, scan through the blocks again to fill in the missing
indices, using the results of the previous step as the initial values.

<img width="80%" src="/assets/reverb/prefix-sums-blocking.svg">

With this strategy, the number of updates is $$u(N) = u(N/B) + N/B + N$$
which solves to $$u(N) \approx \frac {B+1} {B-1} N$$. With a modest block-size,
say $$B = 100$$, we get $$u(N) \approx 1.02 N$$, which is only $$2\%$$ away
from optimal.

In my implementation, I measured a **20% performance improvement by increasing
the block-size from 2 to 100**. I'd call this pretty good, but clearly there's
something else which needs attention.

# Better Cache Utilization
{: #cache-hits}

Each column consists of elements $$D$$ indices apart (i.e. the
$$j$$<sup>th</sup> column consists of elements $$S[D+j]$$, $$S[2D+j]$$,
$$S[3D+j]$$, etc). These elements
are not adjacent in memory, causing our algorithm to have really poor cache
utilization. **Essentially, every lookup of an input element is guaranteed to
be a cache miss**.

To get better cache utilization, we need to try to guarantee that when we
access an element, we also immediately access nearby elements. This suggests
that we should **do multiple adjacent columns together as one unit**, because
physically adjacent elements belong to adjacent columns.

<div class="remark">
We could first [transpose](https://en.wikipedia.org/wiki/Transpose) the
input, turning columns into rows, and therefore guaranteeing that physically
adjacent elements are also part of the same instance of the geometric
prefix-sums. But this would require at least an additional $$2N$$ writes: first
to do the transpose, and then to transpose back again afterwards.
</div>

At a high level, the change we need to make to the algorithm is switching from
1-dimensional blocks (as in the [previous section](#fewer-memory-writes)) to
2-dimensional blocks. It might help to see the illustration below. The
input to the comb is a matrix of $$D$$ columns and $$\lceil N/D \rceil$$ rows.
Focusing on one group of $$K$$ adjacent columns, we break up this group into
blocks of height $$B$$ and width $$K$$. Each block yields $$K$$ block-sums,
and just like before, we recursively compute the geometric prefix-sums of the
block-sums and then expand to produce the output columns.

<img width="100%" src="/assets/reverb/2d-blocked.svg">

<div class="remark">
Be warned: implementing the 2-D blocking strategy is a fiery hell of
off-by-one index arithmetic errors. A part of me is beginning to believe that I
just enjoy this sort of suffering.
</div>

In my implementation, I measured **nearly a $$4\times$$ performance improvement
by doing groups of 100 columns together as one unit**. Wow, now we're getting
somewhere!

# Performance Results
{: #performance}

Above, I described two significant performance optimizations which
[reduced the number of memory updates](#fewer-memory-writes)
and
[increased the number of cache hits](#cache-hits).
Where does that leave us?

Here are the overheads
(with respect to the fast sequential algorithm) for a variety of
different combinations of parameters $$B$$ (block height) and
$$K$$ (block width, i.e. number of adjacent columns). I've marked the
three implementations discussed: the "naive parallel" implementation, and
the two stages of optimizing it. There are a couple other interesting
spots in the design space to consider: for example, if we had
first worked on increasing the number of cache hits ($$B=2$$, $$K=100$$), we
would have seen only a $$2\times$$ performance improvement.
**It's the combination of the two optimizations which gives us the biggest
performance improvement (about $$5\times$$)**.

| B (block height) | K (block width) | Overhead | Notes
|---|---|----------|
| 2 |	1 |	11.9 | "naive parallel" implementation
| 100 |	1 |	9.7 | with "fewer writes" optimization
| 2 |	100 |	5.4 |
| 100 |	100 |	2.6 | with "more cache hits" optimization
| 600 |	600 |	2.4 |

Even in the best configuration, we're still about $$2\times$$ slower than
the fast sequential algorithm. So there's still more work to do. But that
is **much better than the $$12\times$$ overhead we started with**.

Now that we've spent so much time optimizing the sequential overhead of
our comb algorithm, it's time to look at how parallel it is.
As expected, the parallelism is quite good!

<img id="speedup-plot" width="60%" src="/assets/reverb/plot.svg">

In this plot, the "self-speedup" line shows how our algorithm scales relative
to its own 1-processor performance, and the "speedup" line shows scalability
relative to the fast sequential algorithm. Notice that the self-speedup line
is about twice as high as the speedup line, which matches the
approximately $$2\times$$ overhead we measured above.
**In some sense, the self-speedup line shows what we could hope to achieve by
further optimizing the algorithm**. The speedup line shows our current
reality: a maximum improvement over the fast sequential algorithm of about
$$11\times$$.

## Conclusion

With a good comb filter in hand, we get an all-pass filter essentially for
free, and together these filters can be used to simulate a pretty convincing
reverb effect, using Schroeder's reverberator circuit.

In this post, I described the process of designing and implementing
a fast comb filter algorithm.
At first, a naive implementation was an order of magnitude slower than a simple
sequential algorithm. After optimizing the heck out of the parallel
implementation, I got big performance gains ($$5\times$$ improvement), but that
still leaves us with about $$2\times$$ overhead.

The takeaway? Designing a good parallel algorithm often isn't very hard. **The
tricky part is making it competitive with a fast sequential algorithm.**

Work hard, span easy, yall. :v:
