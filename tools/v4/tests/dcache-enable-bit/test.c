/* dcache-enable-bit: does the data-cache enable bit change data-read speed on the 68080?
 *
 * Pointer-chase a 64 KB fast-RAM buffer (fits the data cache) under Disable(), with
 * the data cache as found, explicitly off (CacheControl(0, CACRF_EnableD))
 * and explicitly on. As a baseline that cannot hit the cache, chase a 4 MB
 * buffer. 16384 dependent loads per measurement, best of 8. The raw CACR is read with
 * movec in supervisor mode. The old setting is restored.
 *
 * v4:variant default -O2 -m68080 -fomit-frame-pointer
 */
#include "../akbtest.h"
#include <exec/memory.h>

#define SMALL  65536
#define BIG    (4UL * 1024 * 1024)
#define ROUNDS 8

/* Pointer chase: one long per 64-byte line, lines visited in a random
 * order, so every load waits for the previous one (latency, no prefetch). */
static void build(unsigned long *p, unsigned long bytes)
{
    unsigned long lines = bytes / 64, i, j, t, seed = 12345;
    unsigned long *perm = (unsigned long *)p;     /* use slot 1 of each line as scratch */
    for (i = 0; i < lines; i++) perm[i * 16 + 1] = i;
    for (i = lines - 1; i > 0; i--) {
        seed = seed * 1103515245UL + 12345UL;
        j = (seed >> 8) % (i + 1);
        t = perm[i * 16 + 1]; perm[i * 16 + 1] = perm[j * 16 + 1]; perm[j * 16 + 1] = t;
    }
    for (i = 0; i < lines; i++) {
        unsigned long a = perm[i * 16 + 1], b = perm[((i + 1) % lines) * 16 + 1];
        p[a * 16] = (unsigned long)&p[b * 16];
    }
}

static unsigned long chase(unsigned long *p, unsigned long n)
{
    unsigned long *q = p;
    while (n--) q = (unsigned long *)*q;
    return (unsigned long)q;
}

#define LOADS 16384
static unsigned long timed(unsigned long *p, unsigned long *sum)
{
    unsigned long best = ~0UL, c, r;
    *sum += chase(p, LOADS);                         /* train, fill cache */
    for (r = 0; r < ROUNDS; r++) {
        c = akb_ccc();
        *sum += chase(p, LOADS);
        c = akb_ccc() - c;
        if (c < best) best = c;
    }
    return best;
}

static unsigned long raw_cacr;

static void __attribute__((interrupt)) read_cacr(void)
{
    unsigned long v;
    __asm__ volatile ("movec %%cacr,%0" : "=d"(v));
    raw_cacr = v;
}

static unsigned long cacr(void)
{
    Supervisor((ULONG (*)())read_cacr);
    return raw_cacr;
}

int main(void)
{
    unsigned long *buf, *big, sum = 0, found, off, on, miss;
    unsigned long f0, r0, roff, ron;

    AKB_BEGIN("dcache-enable-bit");
    akb_machine();
    buf = AllocMem(SMALL, MEMF_FAST | MEMF_PUBLIC);
    big = AllocMem(BIG, MEMF_FAST | MEMF_PUBLIC);
    if (!buf || !big) {
        AKB_FAIL("alloc", "no fast RAM");
        return AKB_END();
    }
    build(buf, SMALL);
    build(big, BIG);

    f0 = CacheControl(0, 0);
    r0 = cacr();
    Disable();
    found = timed(buf, &sum);
    CacheControl(0, CACRF_EnableD);
    off = timed(buf, &sum);
    Enable();
    roff = cacr();
    Disable();
    CacheControl(CACRF_EnableD, CACRF_EnableD);
    on = timed(buf, &sum);
    miss = timed(big, &sum);
    Enable();
    ron = cacr();
    CacheControl(f0, CACRF_EnableD);                 /* back as it was */

    AKB_INFO("CacheControl as found $%08lX; raw CACR found $%08lX, EnableD off $%08lX, EnableD on $%08lX, restored $%08lX",
             f0, r0, roff, ron, cacr());
    AKB_VALUE("cycles-as-found", found, "per-16K-loads");
    AKB_VALUE("cycles-enabled-off", off, "per-16K-loads");
    AKB_VALUE("cycles-enabled-on", on, "per-16K-loads");
    AKB_VALUE("cycles-4MB-chase", miss, "per-16K-loads");
    AKB_INFO("sum %lu", sum);
    AKB_CHECK("restored", CacheControl(0, 0) == f0, "CacheControl not restored");
    FreeMem(big, BIG);
    FreeMem(buf, SMALL);
    return AKB_END();
}
