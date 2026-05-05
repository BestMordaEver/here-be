# Characters that pass through any cipher unchanged.
# Everything outside this set + the cipher's own alphabet is dropped.
PASSTHROUGH = frozenset(".,!?-:()")
