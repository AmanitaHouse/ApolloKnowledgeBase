/*
  @PROJECT@ - @WHAT@

  Target: @TARGETS@
  Execution mode: os-friendly (OS calls where available)

  Experimental os-friendly C++ starter. The included interfaces are C and
  are given C linkage in this file. That does not assume a particular NDK
  header provides the linkage itself. This starter does not use the C++
  standard library, exceptions, RTTI, new or delete, or namespace-scope
  objects with constructors. Generating this file does not verify
  compilation, linkage, or hardware execution.
*/

extern "C" {
#include <stdio.h>
#include <dos/dos.h>
#include <exec/execbase.h>
#include <proto/exec.h>

extern struct ExecBase *SysBase;
}

/* ApolloKnowledgeBase os/best-practices/detect-68080-and-fpu-at-run-time.md
   Reviewed applicability: Core 12798-12841, AmigaOS 3.9 and AmigaOS 3.2.
   Recorded measurements: AmigaOS 3.9. ApolloOS R10 and newer cores remain
   intended targets; that article does not demonstrate them. Missing
   measurements do not mean incompatibility. */
static int has_68080(void) { return (SysBase->AttnFlags & (1 << 10)) != 0; }
static int has_fpu(void)   { return (SysBase->AttnFlags & AFF_68881) != 0; }

int main(void)
{
    if (!has_68080()) {
        printf("@PROJECT@ needs an Apollo 68080.\n");
        return RETURN_FAIL;
    }
    printf("@PROJECT@ runs on a 68080 %s.\n", has_fpu() ? "with its FPU" : "with the FPU switched off");

    /* The program starts here. */

    return RETURN_OK;
}
