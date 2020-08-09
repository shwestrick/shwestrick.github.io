---
layout: post
title:  "A Comb Filter is All You Need: Fast Parallel Reverb"
mathjax: true
---

In my quest to develop a range of interesting benchmarks for
[`mpl`](https://github.com/mpllang/mpl) (including for example the
*seam-carver* I described in my
[previous post]({% post_url 2020-07-29-seam-carve %})), I found myself
deep in the rabbit hole of designing a fast parallel algorithm for
artificial reverberation. I've now finished it, and the results are
quite satisfying.

TODO sound clips: original and with reverb, multiple reverb settings.
{: style="color:red"}

Reverb is essentially just a bunch of echoes all mashed together. To
generate these echoes, I used ***comb*** and ***all-pass*** filters, following
a design by
[Manfred Schroeder](https://en.wikipedia.org/wiki/Manfred_R._Schroeder)
as described by
[Curtis Roads](https://en.wikipedia.org/wiki/Curtis_Roads) in
[The Computer Music Tutorial](https://mitpress.mit.edu/books/computer-music-tutorial).
Both comb and all-pass filters produce regular echoes, although their spectral
effects are quite different. By carefully configuring and combining these
filters, we get a convincing artificial reverb effect.

Both types of filters (comb and all-pass) have obvious sequential algorithms
that are fast and extremely easy to implement. Deriving good parallel
algorithms for these filters, however, is not as straightforward.

In this
post, I describe the algorithms I developed and show that they perform well
in practice.

<!--
## Sampling

Real-world audio signals are *analog*. We could model a signal mathematically
by a function $$\mathbb{R} \to \mathbb{R}$$, but this doesn't immediately
translate to a digital world. The next best approximation we can do is to
***sample*** the signal at a regular frequency, and store the "heights"
of these discrete samples.

<img width="80%" src="/assets/reverb/sampling.svg">

It may appear as though sampling a signal *loses
information*, but surprisingly, this is not necessarily the case. In the
first half of the 20<sup>th</sup> century, multiple mathematicians proved that
you can perfectly reconstruct an analog signal as long as the ***sample rate***
is high enough. This result is known is as the
[Nyquist-Shannon sampling theorem](https://en.wikipedia.org/wiki/Nyquist%E2%80%93Shannon_sampling_theorem).

In this post, we'll be dealing with signals represented as sequences $$S$$ of
samples. Each $$S[i]$$ is one sample of the original signal.
For simplicity we will assume that $$i \in \mathbb{Z}$$
can be any integer, either positive or negative, extending as far as we
need in either direction. (Note however that in practice, the sequence will be
represented by an array and will "start" at index 0.)

When we use the notation $$S = \langle x, y, z, \ldots \rangle$$,
the intended meaning is that $$S[i] = 0$$ for all $$i < 0$$, and otherwise
$$S[0] = x$$, $$S[1] = y$$, $$S[2] = z$$, etc.
-->

## Comb Filter

A [feedback comb filter](https://en.wikipedia.org/wiki/Comb_filter#Feedback_form)
produces many equally-spaced echoes of a sound, where each echo is
dimished in intensity. I've drawn an example below. The input
appears first, colored in blue, and each distinct echo is a different color.
(The actual output signal would be the sum of all
these echoes together as one signal.)
<!--
To illustrate the
[impulse response](https://en.wikipedia.org/wiki/Impulse_response)
of the filter, I highlighted the various repeats of one input sample across
multiple echoes. Each sample of the input produces (infinitely) many
equally-spaced, decaying impulses in the output. -->

<img src="/assets/reverb/comb-signal.svg">

Essentially, a comb filter combines two effects: attenuation and delay.

<table class="images">
<tr>
  <td><img src="/assets/reverb/attenuate.svg">Attenuation</td>
  <td><img src="/assets/reverb/delay.svg">Delay</td>
</tr>
</table>

If we were working with analog circuitry, we can achieve both effects at
the same time with a simple feedback loop, as shown below. Each time around
the loop, the signal is delayed
and attenuated (scaled by some $$\alpha \in [0,1]$$).

<img width="70%" src="/assets/reverb/comb.svg">

**Comb Filter Equation**.
When we discrete into samples, the analog circuit can be described
mathematically as the following equation, where
we write $$S[i]$$ for the $$i^\text{th}$$ sample of the input,
and similarly $$C[i]$$ for a sample of the output. The constants
$$D$$ and $$\alpha$$ are respectively the delay (measured in samples) and
attenuation parameters.
{: #comb-equation}

$$
C[i] =
\begin{cases}
  S[i], &i < D \\
  S[i] + \alpha C[i - D], &\text{otherwise} \end{cases}
$$

# Sequential Comb Algorithm
{: #seq-comb}

Imagine feeding samples through the analog circuit shown above. One-by-one, we
take a sample from the input, add to it the value of the feedback loop, and then
pass this along to the output. The values in the feedback loop are easy to
retrieve, because these values were output previously.

Essentially, this computes a comb filter by producing values
$$C[i]$$ with the [equation given above](#comb-equation) in increasing order of
$$i$$ starting with $$i=0$$. In total, we perform $$O(N)$$ operations on an
input of size $$N$$, which is optimal---asymptotically, we can't do any better.

<div class="algorithm" name="(Sequential Comb Filter)">
On input $$S$$ of length $$N$$, sequentially output values $$C[i]$$ according
to [comb filter equation](#comb-equation) for each $$i$$ from $$0$$
to $$N$$.
</div>

<!--
<div class="algorithm">
Here is the
[`mpl`](https://github.com/mpllang/mpl)
code for the sequential comb algorithm.

We represent the input and output signals as
sequences of samples, where each sample is a number in the range
$$[-1,+1]$$. Sequences are basically just arrays; we write `alloc n` allocate a
fresh (uninitialized) sequence of length `n`, and get and set the $$i^\text{th}$$
value of a sequence $$S$$ with `get S i` and `set S i x`.

{% highlight sml %}
(* D: the number of samples to delay in the feedback loop
 * a: the attenuation constant, in range [0,1]
 * S: the sequence of input samples.
 *)
fun sequentialComb (D: int) (a: real) (S: real seq) =
  let
    val n = length S
    val C = alloc n
  in
    for (0, n) (fn i =>
      (* this is executed once for each i from 0 to n-1 *)
      if i < D then
        set C i (get S i)
      else
        set C i (get S i + a * get C (i - D))
    );

    C
  end
{% endhighlight %}
</div>
-->

# Parallelizing Across Columns
{: #par-columns-comb}

Let's look more closely at the
equation $$C[i] = S[i] + \alpha C[i - D]$$. Lurking in plain sight, this
equation contains $$D$$ completely independent computations which can
be computed in parallel.

To see the dependencies within $$C$$ more clearly,
imagine laying out $$C$$ in a matrix,
where at row $$i$$ and column $$j$$ we put $$C[iD + j]$$.
In this layout, each column is a standalone computation, completely independent
of the values in the other columns. For example, as soon as we know the value of
$$C[2]$$, we can immediately compute $$C[D+2]$$ and then $$C[2D+2]$$, etc.

<img width="60%" src="/assets/reverb/comb-columns.svg">

This observation about independent columns immediately suggests
a parallel algorithm:
*do the columns in parallel, and within each column work sequentially
from top to bottom*. This approach
is work-efficient, performing in total $$O(N)$$ operations, which matches
the [sequential algorithm described above](#seq-comb). The span however
is high: each column contains up to $$\lceil N / D \rceil$$ elements, leaving us
with $$O(N/D)$$ span. For small values of $$D$$, this algorithm is not very
parallel at all!

**Is it possible to reduce the span?** The answer is yes!
In the [next section](#geometric-prefix-sums), I'll describe how we can get
more parallelism out of a single column with a parallel algorithm for
*geometric prefix-sums*.

<div class="remark">
[Work and span](https://en.wikipedia.org/wiki/Analysis_of_parallel_algorithms)
are abstract cost measures of a parallel algorithm. The ***work*** is the
total number of operations performed, and the ***span*** is the number of
operations on the critical path (i.e. the longest chain of operations that
must occur sequentially one-by-one).

Given an algorithm with work $$W$$ and span $$S$$, using $$P$$ processors,
we can execute that algorithm in $$O(W/P + S)$$ time. Intuitively,
on each step we perform up to $$P$$ operations (one on each processor), which
makes fast progress on the overall work, but there must be at least $$S$$ steps
overall.
</div>

# Parallelizing Within Columns (Geometric Prefix-Sums)
{: #geometric-prefix-sums }

At first, it might appear as though the computation within
a column is entirely sequential. However, it turns out that there is quite
a lot of parallelism available, similar to
[parallel prefix sums](https://en.wikipedia.org/wiki/Prefix_sum#Parallel_algorithms).

The input elements on the $$j^\text{th}$$ column are elements $$S[iD+j]$$,
and the outputs are $$C[iD+j]$$. Let's simplify by setting $$X[i] = S[iD+j]$$.
Then, abstractly, the problem we're trying to solve is to produce a sequence
$$Y$$ where $$Y[i] = C[iD+j]$$, i.e. the desired output.

With this setup, the [comb filter equation](#comb-equation) gives us the
following recurrence for $$Y$$.

$$
Y[i] = \begin{cases} X[0], &i = 0 \\ X[i] + \alpha Y[i-1], &i > 0 \end{cases}
$$

We can now unroll this recurrence to see that each output element is a
prefix-sum of inputs scaled by powers of $$\alpha$$.

$$
Y[i] = \sum_{k=0}^i \alpha^{i-k} X[k]
$$

Let's call this problem the ***geometric prefix-sums problem***. We
can solve it with following algorithm, which is adapted from an algorithm
for
[parallel prefix sums](https://en.wikipedia.org/wiki/Prefix_sum#Parallel_algorithms).

<div class="algorithm" id="alg-geometric-prefix-sums" name="(Parallel Geometric Prefix-Sums)">
For inputs $$\alpha$$ and $$X$$ and output $$Y$$, we do three steps.
1. In parallel, combine input elements in "blocks" of size 2. Each block
of $$X[i]$$ and $$X[i+1]$$ is transformed into $$\alpha X[i] + X[i+1]$$. These are called the
***block-sums***. Note that there are half as many block-sums as input values,
so we've reduced the problem in half.
2. Recursively compute the geometric prefix-sums of the block-sums.
In the recursive call, we scale by $$\alpha^2$$ instead of $$\alpha$$.
The results of this step are the *odd indices of* $$Y$$.
3. "Expand" to fill in the missing (even) indices by computing
$$Y[i] = X[i] + \alpha Y[i-1]$$ for each even $$i$$.
(The value $$Y[i-1]$$ is one of the outputs of the previous step!)
</div>

Here's an example for an input of size 6.
value $$Y[3]$$ is computed as $$\alpha^2 B_0 + B_1$$, where
$$B_0 = \alpha X[0] + X[1]$$ is the first block-sum, and
$$B_1 = \alpha X[2] + X[3]$$ is the second block-sum.

<img width="80%" src="/assets/reverb/prefix-sums-contraction.svg">

Note that the results of the recursive call are *geometric prefix-sums of
block-sums*. For example, $$Y[3]$$ is the geometric prefix-sum
(using $$\alpha^2$$) of two block-sums (using $$\alpha$$):

<img width="55%" src="/assets/reverb/y3-breakdown.svg">

**Granularity Control**.
This algorithm works for any block-size,
giving us an opportunity for
[granularity control](https://en.wikipedia.org/wiki/Granularity_%28parallel_computing%29).
For a block-size $$B$$, we need to use a scaling factor of
$$\alpha^B$$ in the recursive step (instead of $$\alpha^2$$ as originally
described). Producing
the missing indices in the "expansion" step is also slightly more involved: the
first value within each output block is the same as before, but then we need
to continue scanning through the block to fill in the other nearby missing
indices.

**Cost**.
On an input of size $$M$$, the
[geometric prefix-sums algorithm](#alg-geometric-prefix-sums)
has $$O(M)$$ work and $$O(\log M)$$ span.

# All Together: A Work-Efficient, Highly-Parallel Comb Filter

Combining the two ideas above
(parallelism [across columns](#par-columns-comb) and
[within columns](#geometric-prefix-sums)), we get an algorithm for computing
the comb filter with $$O(N)$$ work and $$O(\log(N/D))$$ span.

<div class="algorithm" name="(Parallel Comb Filter)">
On input $$S$$,
[split the input into columns](#par-columns-comb) and then in parallel compute
the [geometric prefix-sums](#geometric-prefix-sums) of the columns.
</div>

<!--
Concretely, the problem we're trying to solve is to take a column of input
values $$\langle S[i], S[i+D], S[i+2D], \ldots \rangle$$
and produce a column of output values
$$\langle C[i], C[i+D], C[i+2D], \ldots \rangle$$.

<img width="40%" src="/assets/reverb/columns-in-out.svg">

Let's simplify by renaming things a little. Let $$X$$ be the input, with
$$X_0 = S[i]$$, $$X_1 = S[i+D]$$, $$X_2 = S[i+2D]$$, etc. Similarly, let $$Y$$
be the output. Abstractly, then, the problem is to compute:

$$Y_i = X_i + \alpha Y_{i-1}$$

**A Contraction Algorithm**. The idea behind contraction is the solve a
problem recursively, in terms of a smaller version of itself. Specifically,
our goal here is to find new inputs $$X'$$ and $$\alpha'$$, and a new
output $$Y'$$, such that the same equation holds again:

$$Y_j' = X_j' + \alpha' Y_{j-1}'$$

To get there, let's unroll the original equation a little:

$$
\begin{align*}
  Y_i
  &= X_i + \alpha Y_{i-1} \\
  &= X_i + \alpha \color{red}{\left(X_{i-1} + \alpha Y_{i-2}\right)}
  &&\text{(unroll definition of $Y_{i-1}$)} \\
  &= \left(X_i + \alpha X_{i-1}\right) + \alpha^2 Y_{i-2}
  &&\text{(rearrange)}
\end{align*}
$$

Now we're getting somewhere! Do you see it? We can rename the indices a little
to make it clear. Let's use a new index $$j$$ with $$2j+1 = i$$:

$$
\begin{align*}
  Y_i &= \left(X_i + \alpha X_{i-1}\right) + \alpha^2 Y_{i-2}
  \\
  Y_\color{red}{2j+1} &= \left(X_\color{red}{2j+1} + \alpha X_{\color{red}{2j}}\right) + \alpha^2 Y_{\color{red}{2j-1}}
  &&(\text{let}\ 2j+1 = i)
  \\
  \color{red}{Y_j'} &= \left(X_{2j} + \alpha X_{2j-1}\right) + \alpha^2 \color{red}{Y_{j-1}'}
  &&(\text{let}\ Y_j' = Y_{2j+1})
  \\
  Y_j' &= \color{red}{X_j'} + \alpha^2 Y_{j-1}'
  &&(\text{let}\ X_j' = X_{2j+1} + \alpha X_{2j})
  \\
  Y_j' &= X_j' + \color{red}{\alpha'} Y_{j-1}'
  &&(\text{let}\ \alpha' = \alpha^2)
\end{align*}
$$

This sets up the smaller instance of the problem. It is "smaller" in the sense
that $$X'$$ and $$Y'$$ have half as many elements as $$X$$ and $$Y$$.

The output of the smaller instance gives us a bunch of values $$Y_j'$$, which
are each equal to $$Y_{2j+1}$$. That is, **the smaller instance provides the
odd indices of the output**. That leaves us with needing to compute the
even indices, which is easy: for every unknown value at an even index,
there's a known value at the previous odd index which can be used to fill
in the missing value.

<div class="algorithm">
We define a function
$$\textsf{ParallelColumn}(\alpha, X, N)$$ for input $$X$$ of length $$N$$.
The index arithmetic is outrageously tedious, but fairly straightforward.

$$
\begin{array}{l}
&\textsf{ParallelColumn}(\alpha, X, N) =
\\
&~~~~\text{let}~~X' = \big\langle X[2j+1] + \alpha X[2j] : 0 \leq j < \lfloor N / 2 \rfloor \big\rangle
  \\
&~~~~\text{let}~~Y' = \textsf{ParallelColumn}(\alpha^2, X', \lfloor N / 2 \rfloor)
  \\
&~~~~\text{let}~~Y(i) =
    \begin{cases}
      X[0], &i = 0 \\
      Y'[(i-1) / 2], &\text{$i$ odd} \\
      X[i] + \alpha Y'[(i/2)-1], &\text{$i$ even}
    \end{cases}
  \\
&~~~~\text{return}~~\big\langle Y(i) : 0 \leq i < N \big\rangle
\end{array}
$$

In [`mpl`](https://github.com/mpllang/mpl), the code is as follows.
{% highlight sml %}
fun parallelColumn (alpha: real) (X: real seq) =
  if length X <= 1 then
    X
  else
    let
      val N = length X
      val X' = tabulate (N div 2) (fn j =>
        get X (2*j+1) + alpha * get X (2*j)
      )
      val Y' = parallelColumn (alpha * alpha) X'
      val Y = tabulate N (fn i =>
        if i = 0 then
          get X 0
        else if isOdd i then
          get Y' (i div 2)
        else
          get X i + alpha * get Y' (i div 2 - 1)
      )
    in
      Y
    end
{% endhighlight %}
</div>
-->


## All-pass Filter

<img width="80%" src="/assets/reverb/allpass.svg">

An all-pass filter is essentially just a comb filter with some extra
machinery. If $$C$$ is the combed version of signal $$S$$, then the result
of the all-pass on $$S$$ is:

$$
A[i] = -\alpha S[i] + (1 - \alpha^2) C[i - D]
$$

# Implementation

You might have noticed that the feedback loop of the allpass filter is
essentially just a comb filter. This will make our lives much simpler,
as we can reuse the fancy parallel implementation we developed for the
comb filter to generate an allpass filter.

With [`mpl`](https://github.com/mpllang/mpl), this is easy to implement
as follows. The function `tabulate n f` produces a sequence of length
`n` where the $$i^\text{th}$$ element is set to the result of `f i`.
This occurs is parallel, under the hood.
{% highlight sml %}
fun allPass D a S =
  let
    val C = comb D a S
  in
    tabulate n (fn i =>
      (~a * get S i) + (1.0 - a*a) * (if i < D then 0.0 else get C (i - D))
    )
  end
{% endhighlight %}

## Putting it all together

The algorithm described here is one of many reverberators designed by
[Manfred Schroeder](https://en.wikipedia.org/wiki/Manfred_R._Schroeder) during
his time at Bell Labs. Schroeder presented multiple designs, but we will only
be considering one of them here.

Schroeder's design consists of two primary components: a *global reverator* and
a *tapped delay*. The goal of the global reverberator is to simulate the
overall response of a room, where there are thousands of echoes all
mixed together into a lush soup so dense that no one echo is distinctly
discernable. In contrast, the tapped delay produces just a few clearly distinct
echoes which reflect the sound straight back to the listener, simulating
a hard, flat wall in the back of the room. These are called
"early reflections" because they arrive first, almost immediately after the
original sound occurs. The global reverberation kicks in a moment later, and
then gradually dies down.

**Global Reverberator**. The overall design of the global reverberator is to
use four comb filters in parallel, followed by two allpass filters in series,
as shown in the following diagram.

<img width="80%" src="/assets/reverb/design.svg">
