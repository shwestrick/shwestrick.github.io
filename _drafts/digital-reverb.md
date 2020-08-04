---
layout: post
title:  "Implementing Parallel Digital Reverberation"
mathjax: true
---

Everyone is familiar with reverberation, or *reverb* for short. It's the
difference between singing in a closet and singing in a bathroom.
When you yell into a canyon and (after a moment) hear your voice echoed
back at you, this is essentially a form of reverb. What you're hearing
is your voice *reflected* back at you by hard surfaces on the other side
of the canyon.

All rooms are just tiny
canyons, with a lot more surfaces, and at much closer distances. Each surface
provides a different echo, which might come straight back to your ears, or
might bounce around the room for a while before you hear it. To simulate
the feeling of a room, we just need to simulate all of its
surfaces, and how these surfaces interact with one another, to create echoes
and resonances of the original sound.

Typical rooms have a lot of surfaces at weird angles (tables, chairs, etc.)
and just a few big flat surfaces, such as its four walls and ceiling. Roughly
speaking, we can simulate the sound of the big flat surfaces with just a
few "early reflections" of the sound, largely unmodified. For all of the
weird surfaces, we can generate

For decades now, reverb has been a quintessential component of digital sound
processing software. Many ways to generate digital reverb...

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

A comb filter produces periodic echoes of a sound, where each successive
echo is dimished in intensity.

<img width="70%" src="/assets/reverb/comb.svg">

The *comb* filter is so-called because the effect it has on an impulse looks
like a comb. TODO PICTURE

# Implementation

This is the interesting part.

It will be helpful when writing a parallel implementation to convert the
pictoral representation of the comb filter into a mathematical equation
with sequences, as ultimately we represent the signal digitally as a
sequence of samples.

We will think here of a signal $$S$$ as a sequence where $$S[i]$$ is the
$$i^\text{th}$$ element. For simplicity we will assume that $$i \in \mathbb{Z}$$
can be any integer (although in practice, the sequence will be represented by
an array and will "start" at index 0).

Sor a signal $$S$$, attenuation $$\alpha$$, and delay
$$D$$, the combed signal $$S'$$ is given by the following equation.

$$
S'[n] = \sum_{i=0}^\infty \alpha^i S[n - iD]
$$


## Allpass Filter

<img width="80%" src="/assets/reverb/allpass.svg">

# Implementation

You might have noticed that the feedback loop of the allpass filter is
essentially just a comb filter. This will make our lives much simpler,
as we can reuse the fancy parallel implementation we developed for the
comb filter to generate an allpass filter.
