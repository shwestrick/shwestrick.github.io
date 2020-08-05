---
layout: post
title:  "A Parallel Reverberation Algorithm"
mathjax: true
---

Everyone is familiar with reverberation, or *reverb* for short. It's the
difference between singing in a closet and singing in a bathroom.
When you yell into a canyon and (after a moment) hear your voice echoed
back at you, this is essentially a form of reverb. What you're hearing
is your voice *reflected* back at you by hard surfaces on the other side
of the canyon.

If learning about reverb has taught me anything, it's that all rooms are just tiny
canyons, with a lot more surfaces, and at much closer distances. Each surface
provides a different echo, which might come straight back to your ears or
bounce around the room for a while first. To simulate
a room, we need to simulate all of its
surfaces, and how these surfaces interact with one another, to create a bunch
of echoes and resonances of the original sound.

Typical rooms have a lot of surfaces at weird angles (tables, chairs, etc.)
and just a few big flat surfaces, such as its four walls and ceiling. Roughly
speaking, we can simulate the sound of the big flat surfaces with just a
few "early reflections" of the sound, largely unmodified. For all of the
weird surfaces, we can generate

For decades now, reverb has been a quintessential component of digital sound
processing software. Many ways to generate digital reverb...

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

## A Simple Artificial Reverberator

The algorithm described here is one of many reverberators designed by
[Manfred Schroeder](https://en.wikipedia.org/wiki/Manfred_R._Schroeder) during
his time at Bell Labs. Schroeder's reverberators generally consist of two basic
components: ***comb*** and ***allpass*** filters (described in more detail in
the next section).

Generally speaking, the comb filters are used to generate
multiple reflections of the sound at various frequencies, and the allpass
filters help compound these reflections to generate a vast collection of
***fused reflections*** of the source signal. These fused reflections can
be mixed with the original signal to simulate reverberation.

Schroeder presented multiple designs, but we will only be considering one of
them here. The overall design is to use four comb filters in parallel,
followed by two allpass filters in series, as shown in the following
diagram.

<img width="80%" src="/assets/reverb/design.svg">

## Comb Filter

A [comb filter](https://en.wikipedia.org/wiki/Comb_filter) is essentially an
echo generator. It produces periodic echoes of
a sound, where each successive echo is dimished in intensity.
This combines two effects: *attenuation* and *delay*.
Attenuating a signal makes it less intense, and delaying a signal makes it
"start" later.

<table class="images">
<tr>
  <td><img src="/assets/reverb/attenuate.svg">Attenuation</td>
  <td><img src="/assets/reverb/delay.svg">Delay</td>
</tr>
</table>

If we look at a single sample from the original signal, a comb filter will cause
that sample to be repeated again and again at regular intervals, each time
smaller than before.

<img src="/assets/reverb/comb-signal.svg">

# Analog Circuit

Implementing a comb filter with an analog circuit is extremely simple, as
shown below. Using
a feedback loop, we can cause the signal to echo at regular intervals.
An attenuation parameter $$\alpha \in [0,1]$$ controls the intensity of each
successive echo.

<img width="70%" src="/assets/reverb/comb.svg">

# Discretizing the Comb

For a (sampled) signal $$S$$, attenuation $$\alpha$$, and delay duration
$$D$$ (measured in samples), the samples of the combed signal $$S'$$ are given
by the following equation.

$$
S'[i] = \sum_{j=0}^\infty \alpha^j S[i - jD]
$$

To see why this is correct, let's walk through a small example.
Imagine running a signal through the circuit shown above
with a delay duration of $$D = 1$$ sample.
We'll write $$S = \langle s_0, s_1, s_2, \ldots \rangle$$ for the samples of
this signal. If we pause the circuit at each sample point and measure the
wires, we would see the following (showing the first three
samples):

<img width="70%" src="/assets/reverb/comb-steps.svg">

Initially, the first sample $$s_0$$ flows on the input through
to the output. On the next sample point, $$s_1$$ flows on the input and is
combined with the delayed $$\alpha s_0$$ from the feedback loop, producing
$$s_1 + \alpha s_0$$ on the output. This is fed back through the loop and
attenuated by $$\alpha$$, so that on the final sample point, $$s_2$$ is
combined with $$\alpha s_1 + \alpha^2 s_0$$ to produce
$$s_2 + \alpha s_1 + \alpha^2 s_0$$ on the output.

Altogether, on input $$S$$ with a delay time of one sample, we see that the
resulting signal $$S'$$ is

$$
S' = \langle s_0,\ s_1 + \alpha s_0,\ s_2 + \alpha s_1 + \alpha^2 s_0,\ \ldots \rangle
$$

# Parallel Implementation of a Comb Filter

Using the equation $$S'[i] = \sum_{j=0}^\infty \alpha^j S[i - jD]$$, we'll now
derive a parallel algorithm for a comb filter. Our goal is

The most obvious approach would be to compute exactly what the equation says,
i.e. allocate an array and set each index to $$S'[n]$$. But for an

<!-- <div class="algorithm">
**Bad Comb Algorithm**

Inputs:
  * array $$S$$ of $$N$$ samples
  * attenuation $$\alpha$$
  * delay $$D$$ (measured in samples)

Output: array $$S'$$ of $$N$$ samples

Algorithm:
1. Allocate output array $$S'$$
2. In parallel for each $$0 \leq n < N$$:
  * Set $$S'[n] \gets \sum_{i=0}^{\left\lfloor{n/D}\right\rfloor} \alpha^i S[n - iD]$$
</div> -->

## Allpass Filter

<img width="80%" src="/assets/reverb/allpass.svg">

# Implementation

You might have noticed that the feedback loop of the allpass filter is
essentially just a comb filter. This will make our lives much simpler,
as we can reuse the fancy parallel implementation we developed for the
comb filter to generate an allpass filter.
