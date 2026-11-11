# Makefile PowerShell wrapper

# This file provides the same targets as Makefile for Windows PowerShell.
# It simply forwards calls to the Makefile using make.exe if available,
# otherwise runs the equivalent commands directly.

param(
    [Parameter(Mandatory=$true)][ValidateSet('install','dev','backend','frontend','test','lint','check','migrate','e2e','api-types')]
    $Target
)

switch ($Target) {
    'install'   { .\Makefile install }
    'dev'       { .\Makefile dev }
    'backend'   { .\Makefile backend }
    'frontend'  { .\Makefile frontend }
    'test'      { .\Makefile test }
    'lint'      { .\Makefile lint }
    'check'     { .\Makefile check }
    'migrate'   { .\Makefile migrate }
    'e2e'       { .\Makefile e2e }
    'api-types' { .\Makefile api-types }
    default { Write-Error "Unknown target: $Target" }
}

