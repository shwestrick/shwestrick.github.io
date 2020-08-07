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
the loop, the signal is delayed and attenuated. The amount of delay and
attenuation is configurable. In this case, the attenuation parameter
$$\alpha \in [0,1]$$ is shown explicitly below.

<img width="70%" src="/assets/reverb/comb.svg">

# Sequential Comb Algorithm

To get a sequential algorithm for a comb filter, we can imagine feeding
samples through the analog circuit shown above. One-by-one, we take a sample
from the input, add to it the value of the feedback loop, and then pass this
along to the output. The values in the feedback loop are easy to retrieve,
because these values were output previously.

<div class="algorithm">
Here is the
[`mpl`](https://github.com/mpllang/mpl)
code for this algorithm. We represent the input and output signals as
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
      (* this is executed for each i from 0 to n-1 *)
      if i < D then
        set C i (get S i)
      else
        set C i (get S i + a * get C (i - D))
    );

    C
  end
{% endhighlight %}
</div>

# A Simple (But Inefficient) Parallel Comb

For a sequence of samples $$S$$, attenuation $$\alpha$$, and delay duration
$$D$$ (measured in samples), the combed samples $$C$$ are given
by the following equation.

$$
C[i] = \sum_{j=0}^{\lfloor i / D \rfloor} \alpha^j S[i - jD]
$$

This formula essentially describes a naive parallel algorithm where
each element of the outpt is computed as a sum of $$i/D$$ terms from
the input. In terms of
[work and span](https://en.wikipedia.org/wiki/Analysis_of_parallel_algorithms),
computing each element in this manner takes $$O(i/D)$$ work
and $$O(\log (i/D))$$ span.

<div class="remark">
Computing a summation can be done in parallel
by dividing the items into two sets, recursively computing the summation
of the two sets in parallel, and then adding the results. This takes
linear work and logarithmic span.
</div>

In total, this adds up to $$O(n^2 / D)$$ work
and $$O(\log (n/D))$$ span for an input of size $$n$$.
**Although the span is good, the work of this
naive algorithm is too expensive.** In comparison, the sequential comb
algorithm described above takes only $$O(n)$$ work, so this simple parallel
algorithm is *work-inefficient* by a factor of $$O(n/D)$$. For small values
of $$D$$, this is especially bad, and small values of $$D$$ are going to be
the norm for our ultimate reverb algorithm! **We need a better algorithm.**

# A

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
