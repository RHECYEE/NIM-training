<#
.SYNOPSIS
    One command. Gets everything you need to start drawing the seven fires.

.DESCRIPTION
    Run this when you sit down at the laptop, before you open ArcGIS Pro.

      1. Finds the ArcGIS Pro Python
      2. Builds the GeoOps incident folder tree
      3. Fetches the AOI's vector base data from public REST services
     3b. Fetches the leased property's 12 parcels from the county
      4. Regenerates the AOI definition
      5. Builds the blank Event geodatabase with the correct schema and domains
      6. Builds an ArcGIS Pro project with every layer loaded and the CRS set
      7. Runs the whole pipeline against the test fixtures so you have seen it work
      8. Tells you exactly what to do next

    Everything is idempotent. Run it again any time; it skips what is already done.

.PARAMETER IncidentRoot
    Where the incident folder tree goes. Default: D:\incidents, falling back to
    <UserProfile>\Documents\incidents if D: does not exist.

.PARAMETER SkipFetch
    Do not hit the network. Use the base data already on disk.

.PARAMETER Force
    Refetch base data and rebuild the Pro project even if they already exist.

.PARAMETER OpenPro
    Launch ArcGIS Pro on the finished project when everything is done.

.EXAMPLE
    .\Start-StormMountain.ps1

.EXAMPLE
    Double-click START.cmd - the normal way to run this. It wraps this script
    so Windows' default execution policy does not block it.

.EXAMPLE
    .\Start-StormMountain.ps1 -OpenPro

.EXAMPLE
    .\Start-StormMountain.ps1 -IncidentRoot C:\fire -Force

.NOTES
    TRAINING EXERCISE - NOT AN ACTUAL INCIDENT.
#>

[CmdletBinding()]
param(
    [string]$IncidentRoot,
    [switch]$SkipFetch,
    [switch]$Force,
    [switch]$OpenPro
)

$ErrorActionPreference = 'Stop'
$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$script:Failures = @()

# Several scripts take repo-relative paths (data/fixtures). Run from the repo
# root so those resolve no matter where this was invoked from, and put the
# caller back where they started on the way out.
Push-Location $RepoRoot
trap { Pop-Location; break }

function Write-Step  { param($n, $t) Write-Host "`n[$n] $t" -ForegroundColor Cyan }
function Write-Ok    { param($t) Write-Host "    $t" -ForegroundColor Green }
function Write-Note  { param($t) Write-Host "    $t" -ForegroundColor Gray }
function Write-Warn2 { param($t) Write-Host "    $t" -ForegroundColor Yellow }
function Write-Bad   { param($t) Write-Host "    $t" -ForegroundColor Red; $script:Failures += $t }

Write-Host ""
Write-Host "  Storm Mountain Training Grounds" -ForegroundColor White
Write-Host "  TRAINING EXERCISE - NOT AN ACTUAL INCIDENT" -ForegroundColor Yellow
Write-Host "  7 fires x 16 products = 112 sheets" -ForegroundColor Gray
Write-Host ""

# ---------------------------------------------------------------- 1. Python --
Write-Step 1 "Locating Python"

# The Pro Python has arcpy. A plain Python does not, but it can still run
# everything except the geodatabase and export steps - so find both, and use
# whichever each step actually needs.
$ProPythonCandidates = @(
    "$env:ProgramFiles\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe",
    "${env:ProgramFiles(x86)}\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe",
    "$env:LOCALAPPDATA\Programs\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe",
    "C:\Program Files\ArcGIS\Pro\bin\Python\envs\arcgispro-py3\python.exe"
)
$ProPython = $ProPythonCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($ProPython) {
    Write-Ok "ArcGIS Pro Python: $ProPython"
} else {
    Write-Warn2 "ArcGIS Pro Python not found in the usual places."
    Write-Note "Steps needing arcpy will be skipped. Everything else still runs."
    Write-Note "If Pro is installed somewhere unusual, edit `$ProPythonCandidates at the top of this script."
}

$AnyPython = $ProPython
if (-not $AnyPython) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { $AnyPython = $cmd.Source }
}
if (-not $AnyPython) {
    Write-Bad "No Python at all. Install ArcGIS Pro, or python.org, then re-run."
    Write-Host ""
    Pop-Location
    exit 1
}
Write-Ok "Using for scripts: $AnyPython"

# pyyaml is needed by several scripts and ships with Pro's environment.
& $AnyPython -c "import yaml" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Warn2 "pyyaml missing. Installing into the user site-packages..."
    & $AnyPython -m pip install --user --quiet pyyaml
    if ($LASTEXITCODE -ne 0) {
        Write-Bad "Could not install pyyaml. Run: $AnyPython -m pip install --user pyyaml"
    } else {
        Write-Ok "pyyaml installed"
    }
} else {
    Write-Ok "pyyaml present"
}

# ------------------------------------------------------------ 2. Folder tree --
Write-Step 2 "Incident folder tree"

if (-not $IncidentRoot) {
    $IncidentRoot = if (Test-Path 'D:\') { 'D:\incidents' }
                    else { Join-Path $env:USERPROFILE 'Documents\incidents' }
}
# Folder name matches what make_folder_structure.py derives from config/fires.yml.
$IncidentDir  = Join-Path $IncidentRoot "2026_StormMountain"

if (Test-Path $IncidentDir) {
    Write-Ok "Already exists: $IncidentDir"
} else {
    New-Item -ItemType Directory -Path $IncidentRoot -Force | Out-Null
    & $AnyPython (Join-Path $RepoRoot 'scripts\make_folder_structure.py') --dest $IncidentRoot
    if ($LASTEXITCODE -eq 0) { Write-Ok "Created: $IncidentDir" }
    else { Write-Bad "Folder tree failed." }
}

$BaseData     = Join-Path $IncidentDir 'base_data'
$IncidentData = Join-Path $IncidentDir 'incident_data'
$ProductsDir  = Join-Path $IncidentDir 'products\pdf'
$EventGdb     = Join-Path $IncidentData 'event.gdb'

# -------------------------------------------------------------- 3. Base data --
Write-Step 3 "Base data for the AOI"

if ($SkipFetch) {
    Write-Note "Skipped (-SkipFetch)."
} else {
    $fetchArgs = @((Join-Path $RepoRoot 'scripts\fetch_base_data.py'), '--out', $BaseData)
    if ($Force) { $fetchArgs += '--force' }
    & $AnyPython @fetchArgs
    if ($LASTEXITCODE -eq 0) { Write-Ok "Vector base data in $BaseData" }
    else { Write-Warn2 "One or more layers failed. Check the output above; the rest still landed." }
}

# ------------------------------------------------------ 3b. Leased property --
Write-Step "3b" "Leased property (23740 Storm Mountain Rd)"

$siteArgs = @((Join-Path $RepoRoot 'scripts\fetch_site.py'))
if ($Force) { $siteArgs += '--force' }
& $AnyPython @siteArgs
if ($LASTEXITCODE -eq 0) {
    Write-Ok "12 patented mining claims, 246.54 ac -> data\site\"
    Write-Warn2 "The fire district boundary runs THROUGH the property."
    Write-Note "Sections 14/15 (9 claims): Rockerville FD, Keystone Ambulance"
    Write-Note "Section 10   (3 claims): Whispering Pines FD, NO ambulance district on record"
    Write-Note "Read docs\11-leased-property.md before you brief anything."
} else {
    Write-Warn2 "Parcel fetch failed. The committed copy in data\site\ still works."
}

# --------------------------------------------------------------------- 4. AOI --
Write-Step 4 "AOI definition"
& $AnyPython (Join-Path $RepoRoot 'scripts\make_aoi.py')
if ($LASTEXITCODE -ne 0) { Write-Bad "make_aoi.py failed." }

# ------------------------------------------------------------- 5. Event GDB --
Write-Step 5 "Event geodatabase"

if (-not $ProPython) {
    Write-Warn2 "Skipped - needs arcpy."
} elseif (Test-Path $EventGdb) {
    Write-Ok "Already exists: $EventGdb"
    Write-Note "Delete it, or pass --overwrite to build_event_gdb.py, to rebuild."
} else {
    & $ProPython (Join-Path $RepoRoot 'scripts\arcpy\build_event_gdb.py') --dest $IncidentData
    if ($LASTEXITCODE -eq 0) { Write-Ok "Created: $EventGdb" }
    else { Write-Bad "Event geodatabase build failed." }
}

# ----------------------------------------------------------- 6. Pro project --
Write-Step 6 "ArcGIS Pro project"

$Aprx = Join-Path $IncidentDir "projects\StormMountain.aprx"

if (-not $ProPython) {
    Write-Warn2 "Skipped - needs arcpy. You will have to add the layers by hand."
} elseif ((Test-Path $Aprx) -and -not $Force) {
    Write-Ok "Already exists: $Aprx"
    Write-Note "Pass -Force to rebuild it from the fetched data."
} else {
    $projArgs = @((Join-Path $RepoRoot 'scripts\arcpy\build_project.py'), '--incident', $IncidentDir)
    if ($Force) { $projArgs += '--overwrite' }
    & $ProPython @projArgs
    if ($LASTEXITCODE -eq 0) {
        Write-Ok "Built: $Aprx"
        Write-Note "Base data converted to a geodatabase, map already in UTM 13N,"
        Write-Note "layers loaded in draw order, Event layers on top ready to edit."
    } else {
        Write-Bad "Project build failed. Add the layers by hand, or check the output above."
    }
}

# ---------------------------------------------------------------- 7. Dry run --
Write-Step 7 "Pipeline dry run against the test fixtures"
Write-Note "Throwaway geometry. Proves the pipeline works before you draw anything real."

& $AnyPython (Join-Path $RepoRoot 'scripts\make_fires.py') | Out-Null
& $AnyPython (Join-Path $RepoRoot 'scripts\derive_tactical.py') --all --in data/fixtures
& $AnyPython (Join-Path $RepoRoot 'scripts\validate_event_data.py')
if ($LASTEXITCODE -eq 0) { Write-Ok "Pipeline healthy." }
else { Write-Bad "Validation failed on the fixtures - fix this before drawing." }

# ------------------------------------------------------------------ 8. Next --
Write-Step 8 "What to do next"

$trails = Join-Path $BaseData 'trails.geojson'
$roads  = Join-Path $BaseData 'roads.geojson'

Write-Host @"

    1. Get the NWCG GeoOps template if you have not already. It ships the
       blank Event GDB, the official .lyrx symbology and the layout templates.
       https://www.nwcg.gov/page/geospatial-training-unit-tools
       Extract it over: $IncidentDir

    2. Download the DEM by hand (1 m LiDAR if available):
       https://apps.nationalmap.gov/downloader/
       Then:
       & '$ProPython' '$RepoRoot\scripts\arcpy\derive_terrain.py' --dem <dem.tif> --out '$BaseData\elevation'

    3. Open the project. Everything is already loaded and the map is in UTM 13N:
       $Aprx

       One thing still manual: repair the Event .lyrx paths from the GeoOps
       template to point at $EventGdb, so the official symbology and feature
       templates come through.

    4. Draw the seven fires. Open this and work from it:
       $RepoRoot\docs\10-digitizing-guide.md
       And read this once before you start, for the property itself:
       $RepoRoot\docs\11-leased-property.md

       Short version - you draw:
         - 7 perimeter polygons (FeatureCategory = Wildfire Daily Fire Perimeter)
         - helispots, dip sites, safety zones
         - drop point LOCATIONS with a DIVISION value, but NO numbers
         - division and branch breaks, and at least one Access Route
         - set LINE_STATUS on trails/roads you are holding as line
       The pipeline derives hand line, road-as-line, the fire edge and the
       drop point numbers.

    5. Derive, per fire:
       & '$ProPython' '$RepoRoot\scripts\arcpy\derive_tactical.py' --gdb '$EventGdb' --fire Red ``
           --trails '$trails' --roads '$roads'

    6. Build all 112 products:
       & '$ProPython' '$RepoRoot\scripts\arcpy\export_products.py' --aprx <project.aprx> ``
           --out '$ProductsDir' --all-fires

"@ -ForegroundColor White

# ---------------------------------------------------------------- summary --
Write-Host ("  " + ("-" * 66)) -ForegroundColor DarkGray
if ($script:Failures.Count -gt 0) {
    Write-Host "  $($script:Failures.Count) step(s) failed:" -ForegroundColor Red
    $script:Failures | ForEach-Object { Write-Host "    - $_" -ForegroundColor Red }
    Write-Host ""
    Pop-Location
    exit 1
}

if ($OpenPro -and (Test-Path $Aprx)) {
    Write-Host "  Opening ArcGIS Pro..." -ForegroundColor Cyan
    Start-Process $Aprx
}

Write-Host "  Ready. Incident root: $IncidentDir" -ForegroundColor Green
if (Test-Path $Aprx) { Write-Host "  Project: $Aprx" -ForegroundColor Green }
Write-Host "  TRAINING EXERCISE - NOT AN ACTUAL INCIDENT" -ForegroundColor Yellow
Write-Host "  Never sync this to NIFS or NIFC AGOL. No real IRWIN ID, ever." -ForegroundColor Yellow
Write-Host ""
Pop-Location
exit 0
