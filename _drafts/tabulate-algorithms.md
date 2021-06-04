---
layout: post
title:  "Hiding Mutation Behind a Pure Interface"
mathjax: true
---

In my research on parallel functional programming, I spend a lot of time
thinking about "mutation", the ability to modify data in-place.
Mutation is dangerous for parallel programming because of the
possibility of race conditions, which (as perhaps you are unfortunately
familiar) are notoriously difficult to detect and debug.

Perhaps we could throw out mutation altogether? Go *purely functional* and
never look back?

Well, to put it bluntly, this just doesn't work. There are many examples of
"real-world" programming languages that admirably attempted to be purely
functional but eventually backtracked. Haskell is the most well-known example:
in the old days, Haskell

The idea might seem reasonable, but time and time again, people have tried
to do just this, and never followed through.
Time and time again, people have tried and failed.

If we didn't care about efficiency, this might be a reasonable
approach. But we *do* care about efficiency! After all, we're talking about
parallelism here: making things fast is the whole point.


And as we'll see below,
the performance consequences of throwing out mutation are too drastic. So no,
we can't throw it out. I'm afraid mutation is here to stay.

Instead, we need a way of utilizing mutation without accidentally shooting
ourselves in the foot. The most effective technique I've seen is to use
it but hide it, behind a "pure" interface.

##

